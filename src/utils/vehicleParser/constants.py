ENGINE_HP_AB_MUL_TANK = 1.908
ENGINE_SPEED_AB_MUL_TANK = 1.101
ENGINE_SPEED_AB_MUL_SHIP = 1.222
ENGINE_SPEED_AB_MUL_AIR = 1.037

CANNON_TYPE = 'bullet'
ROCKET_TYPE = 'rocketGun'
TORPEDO_TYPE = 'torpedoGun'
BOMB_TYPE = 'bombGun'
BOOSTER_TYPE = 'boosterGun'
CONTAINER_TYPE = 'container'
EXTFUELTANK_TYPE = 'fuelTankGun'

CANNON_NAME = 'cannon'
ROCKET_NAME = 'rocket'
TORPEDO_NAME = 'torpedo'
BOMB_NAME = 'bomb'
BOOSTER_NAME = 'payload'
CONTAINER_NAME = 'container'
EXTFUELTANK_NAME = 'payload'

THERMAL_VISION_GENERATIONS: dict = {
    (500, 300): "GEN1",
    (800, 600): "GEN2",
    (1024, 768): "GEN2+",
    (1200, 800): "GEN3",
    (1920, 1080): "GEN3+",
}

IR_VISION_GENERATIONS: dict = {
    (800, 600): "GEN1",
    (1024, 768): "GEN2",
    (1200, 800): "GEN2+",
    (1600, 1200): "GEN3",
    (1920, 1080): "GEN3+",
}

GROUND_TYPES: set[str] = {'light_tank', 'medium_tank', 'heavy_tank', 'tank_destroyer', 'spaa'}
AIR_TYPES: set[str] = {'fighter', 'assault', 'bomber', 'helicopter'}
SEA_TYPES: set[str] = {'destroyer', 'submarine_chaser', 'cruiser', 'battleship', 'gun_boat', 'torpedo_boat', 'torpedo_gun_boat', 'naval_ferry_barge'}

AIR_TYPES2: set[str] = {"attack_helicopter", "utility_helicopter", "fighter", "assault", "bomber"}
GROUND_TYPES2: set[str] = {"tank", "light_tank", "medium_tank", "heavy_tank", "tank_destroyer", "spaa", "lbv", "mbv", "hbv", "exoskeleton"}
SEA_TYPES2: set[str] = {"ship", "destroyer", "light_cruiser", "boat", "heavy_boat", "barge", "frigate", "heavy_cruiser", "battlecruiser", "battleship", "submarine"}

AIR_CLASSES = ["exp_fighter", "exp_bomber", "exp_assault", "exp_helicopter"]
GROUND_CLASSES = ["exp_tank", "exp_tank_destroyer", "exp_SPAA", "exp_heavy_tank"]
SEA_CLASSES = ["exp_cruiser", "exp_destroyer", "exp_gun_boat", "exp_torpedo_boat", "exp_submarine_chaser", "exp_torpedo_gun_boat", "exp_naval_ferry_barge"]
