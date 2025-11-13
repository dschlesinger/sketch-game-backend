import random

# Load Data on init

with open('fantasy_firstNames_male.txt', 'r') as ffm:

    male_names = ffm.read().splitlines()


with open('fantasy_lastNames.txt', 'r') as fln:

    last_names = fln.read().splitlines()

combined = male_names + last_names

def name_province() -> str:

    return random.choice(combined)

def name_faction() -> str:

    return f'The {random.choice(combined)} {random.choice(combined)}'