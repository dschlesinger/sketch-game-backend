import matplotlib.pyplot as plt
import numpy as np
import scipy as sp
import sys
from shapely import Polygon
import shapely
import random
import uuid
from typing import Set, List

from create_game.schema import GameState, Province, Faction, \
                               City, Army, Port, Fort, \
                               get_province, get_province_by_fractal
from create_game.naming import name_province

def run_voronoi(grain: int = 100):
    """https://stackoverflow.com/questions/28665491/getting-a-bounded-polygon-coordinates-from-voronoi-cells"""

    eps = sys.float_info.epsilon

    towers = np.random.rand(grain, 2)
    bounding_box = np.array([0., 1., 0., 1.]) # [x_min, x_max, y_min, y_max]

    def in_box(towers, bounding_box):
        return np.logical_and(np.logical_and(bounding_box[0] <= towers[:, 0],
                                            towers[:, 0] <= bounding_box[1]),
                            np.logical_and(bounding_box[2] <= towers[:, 1],
                                            towers[:, 1] <= bounding_box[3]))


    def voronoi(towers, bounding_box):
        # Select towers inside the bounding box
        i = in_box(towers, bounding_box)
        # Mirror points
        points_center = towers[i, :]
        points_left = np.copy(points_center)
        points_left[:, 0] = bounding_box[0] - (points_left[:, 0] - bounding_box[0])
        points_right = np.copy(points_center)
        points_right[:, 0] = bounding_box[1] + (bounding_box[1] - points_right[:, 0])
        points_down = np.copy(points_center)
        points_down[:, 1] = bounding_box[2] - (points_down[:, 1] - bounding_box[2])
        points_up = np.copy(points_center)
        points_up[:, 1] = bounding_box[3] + (bounding_box[3] - points_up[:, 1])
        points = np.append(points_center,
                        np.append(np.append(points_left,
                                            points_right,
                                            axis=0),
                                    np.append(points_down,
                                            points_up,
                                            axis=0),
                                    axis=0),
                        axis=0)
        # Compute Voronoi
        vor = sp.spatial.Voronoi(points)
        # Filter regions
        regions = []
        for region in vor.regions:
            flag = True
            for index in region:
                if index == -1:
                    flag = False
                    break
                else:
                    x = vor.vertices[index, 0]
                    y = vor.vertices[index, 1]
                    if not(bounding_box[0] - eps <= x and x <= bounding_box[1] + eps and
                        bounding_box[2] - eps <= y and y <= bounding_box[3] + eps):
                        flag = False
                        break
            if region != [] and flag:
                regions.append(region)
        vor.filtered_points = points_center
        vor.filtered_regions = regions
        return vor

    vor = voronoi(towers, bounding_box)

    return vor

def find_neighbors(regions, vertices) -> np.ndarray:

  adjacency_matrix = np.zeros((len(regions), len(regions)))

  beta_provinces = [
      Province(
          province_id=str(uuid.uuid4()),
          fractal_id='-'.join([str(f) for f in r]),
          name=None,
          border=vertices[r + [r[0]], :].tolist(),
          centriod=vertices[r].mean(axis=0).tolist()
      ) for r in regions]

  for i1, r1 in enumerate(regions):

    for i2, r2 in enumerate(regions):

      if r1 == r2:
        continue

      if len(set(r1) & set(r2)) > 0:

        adjacency_matrix[i1, i2] = 1.0

        beta_provinces[i1].neighbors.append(beta_provinces[i2].province_id)

  return adjacency_matrix, beta_provinces

# adj, beta_provinces = find_neighbors(vor.filtered_regions, vor.vertices)

def get_seeds(adj: np.array, n: int = 6, percent_connection_min: float = 0.02):

  continents = {}

  retries: int = 0

  while len(continents) < n:

    if retries > n * 2:
      break

    rn = random.choice(range(adj.shape[0]))

    row = adj[rn]

    if adj.shape[0] * percent_connection_min >= row.sum():
      # this one isnt good enough
      retries += 1
      continue

    continents[str(uuid.uuid4())] = [rn]

  return continents

# seeds = get_seeds(adj)

def expand_continents(adj: np.array, continents, rounds: int = 20):

  for _ in range(rounds):
    for key, tls in continents.items():

      t = random.choice(tls)

      next_possible = np.argwhere(adj[t] == 1.0)

      nxt = random.choice(next_possible[:, -1].tolist())

      tls.append(nxt)

  return continents

# continents = expand_continents(adj, seeds)

def join_continents(continents, provinces, vor):

    used_tiles: Set[int] = set()
    continent_polygons = {}

    civilizations = {}

    for key, tiles in continents.items():

        civilizations[key] = []

        approved_tiles = []
        for t in tiles:
            if t not in used_tiles:
                approved_tiles.append(t)
        
        # Use set() to avoid duplicates *within* this continent
        approved_tiles_unique = set(approved_tiles)
        
        # Add these tiles to the global 'used' set
        [used_tiles.add(at) for at in approved_tiles_unique]

        p = None # This is our polygon accumulator

        for t in approved_tiles_unique: # Loop over the unique tiles
            try:
                # 1. Get the region indices
                region = vor.filtered_regions[t]
                
                # 2. Get vertices, *closing the polygon*
                #    (This matches the logic from your plotting code)
                vertices = vor.vertices[region + [region[0]], :]
                
                # 3. Create the individual tile polygon
                tile_polygon = Polygon(vertices)

                pv = get_province_by_fractal(provinces, '-'.join([str(f) for f in region]))

                pv.name = name_province()
                pv.is_ocean = False
                pv.faction_id = key

                civilizations[key].append(pv)

                # --- THIS IS THE MAIN FIX ---
                # 4. Correctly accumulate the polygons
                if p is None:
                    p = tile_polygon  # Initialize p with the *first* polygon
                else:
                    # Union p with the *next* polygon
                    p = shapely.coverage_union(p, tile_polygon).normalize()
                # ------------------------------

            except shapely.GEOSException as e:
                # It's still possible for errors, so keeping the try/except is smart
                print(f"Warning: GEOSException on tile {t}. Skipping. Error: {e}")
                pass
            except Exception as e:
                # Catch other potential errors
                print(f"Warning: General error on tile {t}. Skipping. Error: {e}")
                pass

        continent_polygons[key] = p

    # Make non continents ocean
    ocean_tiles = list(set())

    return continent_polygons, provinces, civilizations

# Now this should work without the GEOS error
# continent_polygons, provinces, civilizations = join_continents(continents, beta_provinces)

# Make cities
def add_port(pv: Province, provinces: List[Province], p: float = 0.5) -> bool:

  # Randomly dont check
  if not random.uniform(0, 1) > p:

    return False

  for n in pv.neighbors:

    if get_province(provinces, n).is_ocean:

      return True

  return False

def make_cities(civilizations, provinces, city_percent: float = 0.3, army_percent: float = 0.2) -> None:

  for civ, pvs in civilizations.items():

    if not pvs:
      continue

    random.shuffle(pvs)

    # Make Capital
    capital = City(
        is_capital=True
    )

    pvs[0].city = capital

    if add_port(pvs[0], provinces):
      pvs[0].port = Port()

    for i in range(1, int(len(pvs) * city_percent)):

      pvs[i].city = City(
          is_capital=False,
      )

      if add_port(pvs[i], provinces):
        pvs[i].port = Port()

    random.shuffle(pvs)

    for pv in pvs[:int(len(pvs) * army_percent)]:

      pv.fort = Fort()

      pv.army = Army(
          faction_id=pv.faction_id,
          numbers=random.choice([50, 100, 150, 200])
      )

# make_cities(civilizations, provinces)