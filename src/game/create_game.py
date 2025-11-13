from game.schema import GameState, Faction
from game.world_builder import run_voronoi, find_neighbors, get_seeds, \
                                   expand_continents, join_continents, \
                                   make_cities
from game.naming import name_faction
import numpy as np

def make_game(game_id: str, owner: str, n_players: int, grain: int = 100) -> GameState:

    vor = run_voronoi(grain=grain)

    adj, beta_provinces = find_neighbors(vor.filtered_regions, vor.vertices)

    seeds = get_seeds(adj, n=n_players)

    continents = expand_continents(adj, seeds)

    continent_polygons, provinces, civilizations = join_continents(continents, beta_provinces, vor)

    # Returns None, inplace edits
    make_cities(civilizations, provinces)

    background_polys = []
    
    for c in list(continent_polygons.values()):
        if c.geom_type == 'Polygon':
            background_polys.append(list(c.exterior.xy))
        elif c.geom_type == 'MultiPolygon':
            for part in c.geoms:
                background_polys.append(list(part.exterior.xy))

    background_polys = [np.array([bpi.tolist() for bpi in bp]).T.tolist() for bp in background_polys]

    factions = [
        Faction(
            faction_id=c,
            name=name_faction(),

            availale=True,
            defeated=False,
            turn_ended=False,
        ) for c in seeds.keys()
    ]

    return GameState(
        game_id=game_id,
        owner=owner,
        game_over=False,
        provinces=provinces,
        factions=factions
    )