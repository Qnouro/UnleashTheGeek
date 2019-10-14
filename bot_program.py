import sys
import math
import copy
import time
from random import randint


width, height = [int(i) for i in input().split()]

NONE = -1
ROBOT_ALLY = 0
ROBOT_ENEMY = 1
HOLE = 1
RADAR = 2
TRAP = 3
AMADEUSIUM = 4
FREE = 0
DIGGING = 1
HQ = 2
PLANTED_RADAR = 3
PLACING0 = 4
PLACING1 = 5
PLACING2 = 6
PLACING3 = 7
PREPARING_TRAP = 8
STATUS_LIST = [FREE, DIGGING, HQ, PLACING0, PLACING1, PLACING2, PLACING3]
NOT_BUSY = [FREE, PLACING0, PLACING1, PLACING2, PLACING3]
PLACING_LIST = [PLACING0, PLACING1, PLACING2, PLACING3]


############################## CLASSES ###############################

class Pos:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f"({self.x}, {self.y})"

    def distance(self, pos):
        return abs(self.x - pos.x) + abs(self.y - pos.y)

    def equal(self, pos):
        return self.x == pos.x and self.y == pos.y

    def nearby(self, position):
        x, y = position.x, position.y
        if self.x == x:
            if self.y <= y+1 and self.y >= y-1:
                return True
        if self.y == y:
            if self.x <= x+1 and self.x >= x-1:
                return True
        return False


class Entity(Pos):
    def __init__(self, x, y, type, id):
        super().__init__(x, y)
        self.type = type
        self.id = id


class Robot(Entity):
    def __init__(self, x, y, type, id, item, status=FREE, stopped=False, simulated=False):
        super().__init__(x, y, type, id)
        self.item = item
        self.status = status
        self.dig_x = -1
        self.dig_y = -1
        self.stopped = stopped
        self.already_simulated = simulated

    def set_simulated(self, simulated):
        self.already_simulated = simulated

    def get_simulated(self):
        return self.already_simulated

    def is_dead(self):
        return self.x == -1 and self.y == -1

    @staticmethod
    def move(x, y, message=""):
        print(f"MOVE {x} {y} {message}")

    @staticmethod
    def wait(message=""):
        print(f"WAIT {message}")

    @staticmethod
    def dig(x, y, message=""):
        print(f"DIG {x} {y} {message}")

    @staticmethod
    def request(requested_item, message=""):
        if requested_item == RADAR:
            print(f"REQUEST RADAR {message}")
        elif requested_item == TRAP:
            print(f"REQUEST TRAP {message}")
        else:
            raise Exception(f"Unknown item {requested_item}")

    def is_in_HQ(self):
        return self.x == 0

    def get_status(self):
        return self.status

    def update(self, x, y, item):
        self.x = x
        self.y = y
        self.item = item

    def update_status(self, status, x=-1, y=-1):
        self.dig_x = x
        self.dig_y = y
        self.status = status
        if status not in STATUS_LIST:
            debug("ERROR UNKNOWN STATUS UPDATE")

    def has_already_stopped(self):
        return self.stopped

    def set_already_stopped(self, stopped):
        self.stopped = stopped


class Cell(Pos):
    def __init__(self, x, y, amadeusium, hole, mark=False, trapped=False):
        super().__init__(x, y)
        self.amadeusium = amadeusium
        self.hole = hole
        self.mark = mark
        self.trapped = trapped
        self.last_seen_amadeusium = "?"
        self.enemy_holed = False
        self.digging_bias = 0

    def get_digging_bias(self):
        return self.digging_bias

    def reset_digging_bias(self):
        self.digging_bias = 0

    def increment_digging_bias(self):
        self.digging_bias += 1

    def has_hole(self):
        return self.hole == HOLE

    def get_amadeusium(self):
        return self.amadeusium

    def update(self, amadeusium, hole):
        self.amadeusium = amadeusium
        self.hole = hole

    def marked(self):
        self.mark = True

    def set_trap(self):
        self.trapped = True

    def get_mark(self):
        return self.mark

    def is_trapped(self):
        return self.trapped

    def update_last_seen(self, new_state):
        self.last_seen_amadeusium = new_state

    def get_last_state(self):
        return self.last_seen_amadeusium

    def set_enemy_hole(self):
        self.enemy_holed = True

    def get_enemy_hole(self):
        return self.enemy_holed


class Grid:
    def __init__(self):
        self.cells = []
        for y in range(height):
            for x in range(width):
                self.cells.append(Cell(x, y, 0, 0))

    def get_cell(self, x, y):
        if width > x >= 0 and height > y >= 0:
            return self.cells[x + width * y]
        return None


class Game:
    def __init__(self):
        self.grid = Grid()
        self.my_score = 0
        self.enemy_score = 0
        self.radar_cooldown = 0
        self.trap_cooldown = 0
        self.radars = []
        self.traps = []
        self.my_robots = []
        self.enemy_robots = []

    def reset(self):
        self.radars = []
        self.traps = []
        self.my_robots = []
        self.enemy_robots = []

    def clear_traps(self):
        self.traps = []

    def clear_radars(self):
        self.radars = []


class Trap(Pos):
    def __init__(self, x, y, trap_net=-1):
        super().__init__(x, y)
        self.neighboor_traps = []  # list of all nearby traps
        self.trapped_bots = []  # list of all nearby bots
        self.trap_net = trap_net  # Index for trap nets.

    def add_neighboor(self, trap):
        self.neighboor_traps.append(trap)

    def detonate(self, detonated_list=[]):
        detonated_list.append(self)
        x,y = self.x, self.y
        max_x, min_x, max_y, min_y = min(29, x+1), max(0, x-1),  min(14, y+1), max(0, y-1)
        exploded_cells = [Pos(x, y), Pos(max_x, y), Pos(min_x, y), Pos(x, max_y), Pos(x, min_y)]
        for trap in self.neighboor_traps:
            exploded = False
            for detonated_trap in detonated_list:
                if trap.equal(detonated_trap):
                    exploded = True
                    break
            if not exploded:  # not exploded yet
                neighboor_explosion = trap.detonate(detonated_list)
                exploded_cells += neighboor_explosion  # might want to optimize this shit
        return exploded_cells

    def set_trap_net_index(self, trap_index):
        self.trap_net = trap_index

    def get_trap_net_index(self):
        return self.trap_net

    def is_neighboor(self, trap):
        x, y = trap.x, trap.y
        if self.x == x:
            if self.y <= y+1 and self.y >= y-1:
                return True
        if self.y == y:
            if self.x <= x+1 and self.x >= x-1:
                return True
        return False

    def is_in_net(self, trap, checked_traps=[]):
        """
        returns True if trap is in this trap net. None otherwise
        """
        if self.equal(trap):
            return self.get_trap_net_index()
        else:
            for neighboor_trap in neighboor_traps:
                checked = False
                # we check if the neighboor is not already checked
                for check_trap in checked_traps:
                    if check_trap.equal(neighboor_trap):
                        checked = True
                        break
                if not checked:
                    return is_in_net(neighboor_trap, trap, checked_traps+[self])

############################ FUNCTIONS ################################


game = Game()
ore_list = []
risky_cells = []
placed_radars_list = []
list_dead_bots = []
adjusted_dig_list = [0, 0, 0, 0, 0]
placing_dict = {}  # saves the last neighbor digging position for the robots
last_grid_state = Grid()
current_radar_bots = []
predefined_radar_pos = [Pos(6, 7), Pos(11, 11), Pos(11, 3), Pos(15, 7), Pos(3, 12), Pos(3, 2), Pos(19, 3), Pos(19, 11), Pos(23, 7), Pos(27, 3), Pos(27, 11),
                        Pos(29, 6), Pos(5, 0), Pos(5, 14), Pos(13, 14), Pos(22, 14), Pos(22, 0), Pos(27, 14), Pos(29, 0)] # Pos(7, 7), Pos(4, 11)
trap_list = []
active_radars_positions = [None]*5
predefined_init_dig_sites = [Pos(3, 1), Pos(3, 4), Pos(3, 10), Pos(3, 13)]

def enemy_path_simulation(game, last_turn_robots):
    """
    Returns a prediction of the enemies' path
    """
    sorted_last_turn_robots = sorted(last_turn_robots, key=lambda x: x.id)
    new_turn_robots = game.enemy_robots

    direction_vectors_list = []  # we will store the last position with its direction vector
    for robot in new_turn_robots:
        if not robot.is_dead():
            index = robot.id%5
            last_pos = Pos(sorted_last_turn_robots[index].x, sorted_last_turn_robots[index].y)
            new_pos = Pos(robot.x, robot.y)
            direction_vector = Pos(new_pos.x - last_pos.x, new_pos.y - last_pos.y)
            direction_vectors_list.append([new_pos, direction_vector])

    return direction_vectors_list


def get_closest_ore(robot):
    """
    Returns the closest available ore to the robot
    """
    global ore_list
    min_dist = 50
    closest_ore = -1
    pos_x, pos_y = 0, 0
    for idx, ore in enumerate(ore_list):
        ore_pos = Pos(ore[0], ore[1])
        distance = robot.distance(ore_pos)
        if min_dist > distance:
            min_dist = distance
            closest_ore = idx
            pos_x, pos_y = ore_pos.x, ore_pos.y
    return closest_ore


def pick_ore(robot):
    """
    Returns a safe ore position for the robot to dig. If none is found, returns
    (-1, -1)
    """
    global ore_list
    if ore_list != []:
        safe = False  # we need this parameter otherwise we give a wrong position
                      # if there is only 1 ore available
        while ore_list != []:
            ore_idx = get_closest_ore(robot)
            ore = ore_list[ore_idx]

            # we verify if cell is safe
            ore_cell = game.grid.get_cell(ore[0], ore[1])
            if ore_cell.get_enemy_hole():
                ore_list.pop(ore_idx)
            elif ore_cell.is_trapped():
                ore_list.pop(ore_idx)
            else:  # safe cell
                if ore[2] == 1:  # no more amadeusium
                    ore_list.pop(ore_idx)
                else:  # remaining amadeusium
                    ore[2] -= 1
                x, y = ore[0], ore[1]
                safe = True
                break
        if ore_list == [] and not safe:  # no ore to pick
            x, y = -1, -1
    else:  # no ore to pick
        x, y = -1, -1
    return x, y


def show_ores(game, x, y):
    """
    Returns a list of all seen ores from the given position (supposedly a radar)
    """
    global risky_cells

    position = Pos(x, y)
    # borders calculations
    border_max_x = min(width, x+5)
    border_min_x = max(0, x-4)
    border_max_y = min(height, y+5)
    border_min_y = max(0, y-4)
    local_ore_list = []

    for j in range(border_min_y, border_max_y):
        for i in range(border_min_x, border_max_x):
            cell = game.grid.get_cell(i, j)
            # We pick the cells in range of the given radar position
            manhattan_distance = cell.distance(position)
            if manhattan_distance <= 4:
                ore = cell.get_amadeusium()
                if ore != "?":  # verifying we can see the cell's infos
                # we mark the cell so we don't write the same ores
                # multiple times. The cell's update are main in the
                # gathering data function
                    if cell.hole:  # if it has a hole when we discover it, we don't take it
                        risky_cells.append(cell)
                        cell.set_enemy_hole()
                    elif int(ore) != 0 and cell.get_mark() == False:
                        local_ore_list.append([i, j, int(ore)])
                        cell.marked()
    return local_ore_list


def holed_by_enemy(cell):  # must recheck logic
    """
    return true if detected hole otherwise false
    """
    if cell.get_enemy_hole():
        return True

    last_state = cell.get_last_state()
    new_state = cell.get_amadeusium()

    # recasting states if integers
    if last_state != "?":
        last_state = int(last_state)
    if new_state != "?":
        new_state = int(new_state)

    if last_state == "?" and isinstance(new_state, int):  # We discover a new cell
        if not cell.hole:
            return False
        else:
            cell.set_enemy_hole()
            return True

    elif isinstance(last_state, int) and isinstance(new_state, int):  # we have already seen this cell
        if int(last_state) != int(new_state):
            cell.set_enemy_hole()
            return True
        return False

    elif last_state == "?" and new_state == "?":  # We don't have vision over the cell
        if cell.hole:
            cell.set_enemy_hole()
            return True
        return False
    return False


def add_command(command, first_param, second_param=None, message=""):
    """
    Adds a command to execute
    """
    global commands_list

    if message == "randomly waiting":
        robot.set_already_stopped(True)
    elif message == "out of hq":
        robot.set_already_stopped(False)

    if second_param is not None:
        commands_list.append([command, first_param, second_param, message])
    elif message != "":
        commands_list.append([command, first_param, message])
    else:
        commands_list.append([command, first_param])


def position_adjustment(robot, status, x, y, loop):
    """
    Adjusts the starting position for the robot.
    """
    index = robot.id%5
    if x>29:  # border of the map. Must be changed
        add_command(robot.dig, robot.x+1, robot.y, "waiting for the game to end")
    if loop > 60:  # advanced in the game
        if adjusted_dig_list[index] < 1:
            x = 12
            save_robot_position(robot, status, x, y)
            adjusted_dig_list[index] = 1
    if loop > 120:  # really advanced in the game
        if adjusted_dig_list[index] < 2:
            x = 20
            save_robot_position(robot, status, x, y)
            adjusted_dig_list[index] = 2
    return x


def initial_move(robot, loop):
    """
    Calculating the positions for the robot to go to
    """
    global placing_dict
    global adjusted_dig_list

    status, x, y = load_robot_position(robot)
    x = position_adjustment(robot, status, x, y, loop)
    robot.update_status(status)
    return status, x, y


def load_robot_position(robot):
    """
    Load the neighboor digging robot's state
    """
    global placing_dict
    global adjusted_dig_list

    index = robot.id%5
    status, x, y = placing_dict[index]
    return status, x, y


def save_robot_position(robot, status, x, y):
    """
    Save the neighboor digging robot's state
    """
    global placing_dict
    global adjusted_dig_list

    placing_dict[robot.id%5] = [status, x, y]


def dig_save_state(robot, stat, x, y, x_next_dig, y_next_dig, message="", x_save_bias=0, y_save_bias=0):
    """
    Digs in the given position and saves the robot's state accordingly.
    x_save_bias: bias if we want the bot to go a different position next time
    instead of the usual scheme
    """
    add_command(robot.dig, x, y, message)  # TODO: IF WE DIG AND ORE_LIST SMALL NOTIFY THE RADAR DIGGERS
    status, x_save, y_save = load_robot_position(robot)
    save_robot_position(robot, stat, x_save + x_save_bias, y_save)
    robot.update_status(stat, x_next_dig, y_next_dig)


def placing0_decision(game, robot):
    """
    Return True if we are done
    """
    cell = game.grid.get_cell(robot.x+1, robot.y)
    enemy_hole = 1 if holed_by_enemy(cell) else 0

    if not cell.is_trapped() and not enemy_hole:  # safe cell
        dig_save_state(robot, PLACING1, robot.x + 1, robot.y, robot.x, robot.y, "Dig-1")
        return True
    else:  # we move to the next state to avoid the cell
        robot.update_status(PLACING1, robot.x, robot.y)
        return False


def placing1_decision(game, robot):
    """
    Return True if we are done
    """
    cell = game.grid.get_cell(robot.x, robot.y-1)
    enemy_hole = 1 if holed_by_enemy(cell) else 0

    if not cell.is_trapped() and not enemy_hole:  # safe cell
        dig_save_state(robot, PLACING2, robot.x, robot.y - 1, robot.x, robot.y - 1, "Dig-2")
        return True
    else:  # we move to the next state
        robot.update_status(PLACING2, robot.x, robot.y-1)
        return False


def placing2_decision(game, robot):
    """
    We don't need to return True as we'll be done anyway.
    """
    cell = game.grid.get_cell(robot.x, robot.y+1)
    enemy_hole = 1 if holed_by_enemy(cell) else 0

    if not cell.is_trapped() and not enemy_hole:  # safe cell
        dig_save_state(robot, PLACING0, robot.x, robot.y + 1, robot.x + 1, robot.y + 1, "Dig-3", 4)

    else:  # we move directly and skip the adjacent case to go farer
        status, x_save, y_save = load_robot_position(robot)
        save_robot_position(robot, PLACING0, x_save+4, y_save)
        robot.update_status(PLACING3, robot.x, robot.y+1)
        dig_neighboors(robot, game, loop)  # we call the function again


def closest_init_pos(robot):
    """
    Returns the closest cell to start digging in.
    """

    global predefined_init_dig_sites

    if predefined_init_dig_sites == []:
        predefined_init_dig_sites.append(Pos(3, 7))  # we want to avoid this cell at turn 0

    min_dist, min_idx = 50, -1
    for idx, cell in enumerate(predefined_init_dig_sites):
        dist = robot.distance(cell)
        if min_dist > dist:
            min_dist = dist
            min_idx = idx

    dig_pos = predefined_init_dig_sites.pop(min_idx)
    return dig_pos.x, dig_pos.y



def dig_neighboors(robot, game, loop):
    """
    Digs in a line by checking the neihbooring cells if they are deemed safe
    """
    global placing_dict
    global adjusted_dig_list

    # initial digging position
    robot_index = robot.id%5
    x_init, y_init = 3, (3*robot_index) + 1

    # Managing the bot's states and positions
    if robot_index in placing_dict:
        # load position for the initial decision
        status, x, y = initial_move(robot, loop)
    else:
        # save new bot
        x, y = closest_init_pos(robot)
        status = PLACING0
        save_robot_position(robot, status, x, y)

    # Updating the bot's status
    robot.update_status(status)
    if not robot.equal(Pos(x, y)):  # heading to digging point
        add_command(robot.move, x, y, "move")
        status, x_save, y_save = load_robot_position(robot)
        save_robot_position(robot, robot.status, x_save, y_save)
        return

    if robot.status == PLACING0:  # We have reached the dig site
        finished_turn = placing0_decision(game, robot)
        if finished_turn:
            return

    if robot.status == PLACING1:  # second dig site
        finished_turn = placing1_decision(game, robot)
        if finished_turn:
            return

    if robot.status == PLACING2:  # last dig site
        placing2_decision(game, robot)
        return

    debug(f"LOGIC PROBLEM FOR ROBOT: {robot.id}")
    # Better make the game crash to see the issue
    exit(1)


def verify_cell_radar(game, x, y):
    """
    Verifies that the given cell is a radar.
    """
    for item in game.radars:
        if item.x == x and item.y == y:
            if item.type == RADAR:
                return True
            return False
    return False


def initiate_game(game, entity_count):
    """
    Initiates the game entities data
    """
    game.reset()

    for i in range(entity_count):
        id, type, x, y, item = [int(j) for j in input().split()]
        if type == ROBOT_ALLY:
            game.my_robots.append(Robot(x, y, type, id, item))
        elif type == ROBOT_ENEMY:
            game.enemy_robots.append(Robot(x, y, type, id, item))
        elif type == TRAP:
            game.traps.append(Entity(x, y, type, id))
        elif type == RADAR:
            game.radars.append(Entity(x, y, type, id))


def fix_prediction(predicted_pos):
    """
    Makes sure the predicted position is in the board
    """
    x, y = predicted_pos.x, predicted_pos.y
    if x < 0:
        x = 0
    elif x > 29:
        x = 29
    if y < 0:
        y = 0
    elif y > 14:
        y = 14
    return Pos(x, y)


def three_step_simulation(robot, game, movement_simulation):
    """
    Returns the score for detonating in the next 2 turns the trap held by the robot
    in one of its adjacent cases.
    """
    x, y = robot.x, robot.y

    # We have to save the score yielded by each of the adjacent cases
    adjacent_cases_score = []
    max_score = -1
    best_position = Pos(-1, -1)
    # The simulations take place on the adjacent cases
    border_max_x, border_min_x = min(x+5, 29)+1, max(x-5, 1)  # we can't mine the first column
    border_max_y, border_min_y = min(y+5, 14)+1, max(y-5, 0)

    for j in range(border_min_y, border_max_y):
        for i in range(border_min_x, border_max_x):
            first_turn_simulation = []
            adjacent_cell = game.grid.get_cell(i, j)
            if adjacent_cell.distance(Pos(x, y)) <= 5:  # we only pick reachable cells in 1 turn
                my_trap = Trap(i, j)

                # We need to add the trap's neighboors
                for trap in trap_list:
                    if my_trap.nearby(trap):
                        my_trap.add_neighboor(trap)

                # We simulate the detonation
                exploded_cells = my_trap.detonate([])

                # We predict the bots' positions
                predicted_positions = []
                for prediction in movement_simulation:
                    last_pos = prediction[0]
                    vector = prediction[1]
                    if vector.x == 0 and vector.y == 0:  # enemy is digging & will likely go backward or is in HQ & will go forward
                        if last_pos.x == 0:
                            vector = Pos(4, 0)
                        else:
                            vector = Pos(-4, 0)
                    predicted_pos = Pos(last_pos.x + vector.x, last_pos.y + vector.y)  # check for x < 0 and y < 0
                    predicted_pos = fix_prediction(predicted_pos)
                    first_turn_simulation.append([predicted_pos, vector])

                for prediction in first_turn_simulation:
                    last_pos = prediction[0]
                    vector = prediction[1]
                    if vector.x == 0 and vector.y == 0:  # enemy is digging & will likely go backward or is in HQ & will go forward
                        if last_pos.x == 0:
                            vector = Pos(4, 0)
                        else:
                            vector = Pos(-4, 0)
                    predicted_pos = Pos(last_pos.x + vector.x, last_pos.y + vector.y)  # check for x < 0 and y < 0
                    predicted_pos = fix_prediction(predicted_pos)
                    predicted_positions.append(predicted_pos)

                # we calculate the score generated by detonating the trap
                score = -1
                killed_bots = []
                for pos in exploded_cells:
                    for my_robot in game.my_robots:
                        if Pos(my_robot.x, my_robot.y).equal(pos):
                            score -= 1

                    for enemy_pos in predicted_positions:
                        if Pos(enemy_pos.x, enemy_pos.y).equal(pos):
                            killed_bots.append(enemy_pos)
                            score += 1

                if score > max_score and not holed_by_enemy(adjacent_cell):
                    max_score = score
                    best_position = adjacent_cell

    return max_score, best_position


def simulate_movement_explosions(robot, game, movement_simulation):
    """
    Returns the score for detonating in the next turn the trap held by the robot
    in one of its adjacent cases.
    """
    x, y = robot.x, robot.y

    # We have to save the score yielded by each of the adjacent cases
    adjacent_cases_score = []
    max_score = -1
    best_position = Pos(-1, -1)
    # The simulations take place on the adjacent cases
    border_max_x, border_min_x = min(x+1, 29)+1, max(x-1, 1)  # we can't mine the first column
    border_max_y, border_min_y = min(y+1, 14)+1, max(y-1, 0)

    for j in range(border_min_y, border_max_y):
        for i in range(border_min_x, border_max_x):
            if i == x or j == y:
                my_trap = Trap(i, j)
                adjacent_cell = game.grid.get_cell(i, j)
                # We need to add the trap's neighboors
                for trap in trap_list:
                    if my_trap.nearby(trap):
                        my_trap.add_neighboor(trap)

                # We simulate the detonation
                exploded_cells = my_trap.detonate([])

                # We predict the bots' positions
                predicted_positions = []
                for prediction in movement_simulation:
                    last_pos = prediction[0]
                    vector = prediction[1]
                    if vector.x == 0 and vector.y == 0:  # enemy is digging & will likely go backward or is in HQ & will go forward
                        if last_pos.x == 0:
                            vector = Pos(4, 0)
                        else:
                            vector = Pos(-4, 0)
                    predicted_pos = Pos(last_pos.x + vector.x, last_pos.y + vector.y)  # check for x < 0 and y < 0
                    predicted_pos = fix_prediction(predicted_pos)
                    predicted_positions.append(predicted_pos)


                # we calculate the score generated by detonating the trap
                score = -1
                killed_bots = []
                for pos in exploded_cells:
                    for my_robot in game.my_robots:
                        if Pos(my_robot.x, my_robot.y).equal(pos):
                            score -= 1

                    for enemy_pos in predicted_positions:
                        if Pos(enemy_pos.x, enemy_pos.y).equal(pos):
                            killed_bots.append(enemy_pos)
                            score += 1

                if score > max_score and not holed_by_enemy(adjacent_cell):
                    max_score = score
                    best_position = adjacent_cell
    return max_score, best_position


def simulate_explosions(trap_list, game):
    """
    returns the score for detonating each trap. The score is positive if the
    detonation is worth it.
    To simulate we need to pick a single trap from the net.
    """
    detonation_list_pos = []
    score_list = []

    # We get a list of all the detonations positions for every trap
    for trap in trap_list:
        detonation_list_pos.append(trap.detonate([]))

    for pos_list in detonation_list_pos:
        score = 0
        output_list = []
        # we will check, for every trap, if a robot is touched and calculate
        # the score of the explosion
        for pos in pos_list:
            for robot in game.my_robots:
                if Pos(robot.x, robot.y).equal(pos):
                    score -= 1
                    output_list.append(robot.id)
            for robot in game.enemy_robots:
                if Pos(robot.x, robot.y).equal(pos):
                    score += 1
                    output_list.append(robot.id)
        score_list.append([score] + output_list)

    return score_list


def score_visualisation(output_list, trap_list):
    """
    Gives a list for null-score traps and strictly positive-score traps
    """
    juicy_list, okay_list = [], []
    for trap, output in zip(trap_list, output_list):
        score = output[0]
        if score==0:
            okay_list.append(Pos(trap.x, trap.y))
        elif score>0:
            juicy_list.append(Pos(trap.x, trap.y))
    return okay_list, juicy_list


def update_game(game):
    """
    We update the game entities info, and simulate the explosions.
    """
    global trap_list

    game.clear_traps()
    game.clear_radars()

    last_turn_robots = copy.deepcopy(game.enemy_robots)

    for i in range(entity_count):
        id, type, x, y, item = [int(j) for j in input().split()]
        if type == ROBOT_ALLY:
            my_robots_list = [robot.id for robot in game.my_robots]
            robot_index = my_robots_list.index(id)
            game.my_robots[robot_index].update(x, y, item)
        elif type == ROBOT_ENEMY:
            enemy_robots_list = [robot.id for robot in game.enemy_robots]
            robot_index = enemy_robots_list.index(id)
            game.enemy_robots[robot_index].update(x, y, item)
        elif type == TRAP:
            game.traps.append(Entity(x, y, type, id))
            # 1- we create the trap list
            trap_list.append(Trap(x, y))
        elif type == RADAR:
            game.radars.append(Entity(x, y, type, id))

    # 2- we create the neighboors for the traps
    create_neighboors()

    # 3- we simulate the explosions and return the resulting lists
    output_list = simulate_explosions(trap_list, game)
    okay_list, juicy_list = score_visualisation(output_list, trap_list)

    # 4- we simulate the enemy movements
    movement_simulation = enemy_path_simulation(game, last_turn_robots)

    for idx, move in enumerate(movement_simulation):
        position = move[0]
        vector = move[1]

    return okay_list, juicy_list, movement_simulation


def create_neighboors():
    """
    Links every trap with its neighboors
    """
    global trap_list
    n = len(trap_list)
    for i in range(n):
        trap1 = trap_list[i]
        for j in range(i+1, n):
            trap2 = trap_list[j]
            if trap1.is_neighboor(trap2):
                trap1.add_neighboor(trap2)
                trap2.add_neighboor(trap1)


def gathering_grid_data(height, width, game, loop):
    """
    Updates the grid's data, and marks risky cells (cells that are digged by
    the enemy).
    """
    for i in range(height):
        inputs = input().split()
        for j in range(width):
            amadeusium = inputs[2 * j]
            hole = int(inputs[2 * j + 1])
            cell = game.grid.get_cell(j, i)
            if loop != 0:
                if cell.get_last_state() != "?" and amadeusium != "?":
                    if int(amadeusium) != int(cell.get_last_state()) - cell.get_digging_bias():
                        cell.set_enemy_hole()
            if not cell.get_enemy_hole() and cell.has_hole():
                if cell.get_last_state() != "?" and amadeusium != "?":
                    if int(amadeusium) != int(cell.get_last_state()) - cell.get_digging_bias():
                        #if we discover a new cell but with a hole
                        cell.set_enemy_hole()
                else:
                    cell.set_enemy_hole()
            cell.update_last_seen(amadeusium)
            cell.update(amadeusium, hole)
            cell.reset_digging_bias()


def select_special_bots(game, turn):
    """
    Updates the list of bots responsible of radars.
    """
    global current_radar_bots
    global placed_radars_list
    global predefined_radar_pos
    global ore_list

    my_robots_list = sorted(game.my_robots, key=lambda x: x.id)
    radar_bot = None

    if turn == 0:  # we choose the closest one
        min_dist, min_idx = 50, -1
        for idx, robot in enumerate(my_robots_list):
            dist = robot.distance(predefined_radar_pos[0])
            if min_dist > dist:
                min_dist = dist
                min_idx = idx
        current_radar_bots.append(my_robots_list[min_idx].id)
        return

    if (len(placed_radars_list) < 10 or len(ore_list) < 6) and len(ore_list) < 12:
        for robot in my_robots_list:
            if (not robot.is_dead()) and robot.x == 0 and (robot.status == FREE or robot.status == HQ and game.radar_cooldown == 0):
                radar_bot = robot
                break

        if radar_bot is not None:
            if radar_bot.id not in current_radar_bots:
                current_radar_bots.append(radar_bot.id)


def bot_is_free(robot):
    """
    Returns true if the bot is free
    """
    return robot.item==NONE or robot.item == AMADEUSIUM


def update_ore_list(game, radar_position):
    """
    Updates the old ore list with the new detected ones
    """
    global ore_list

    radar_x, radar_y = radar_position.x, radar_position.y
    new_ore_list = show_ores(game, radar_x, radar_y)
    ore_list = ore_list + new_ore_list


def get_bias(round):
    """
    Yields a bias depending on the round. Gives a bigger bias when we're close
    to finish the game
    """
    if round <= 10:
        return 0
    elif round <= 20:
        return 4
    elif round <= 50:
        return 8
    elif round <= 120:
        return 12
    else:
        return 16


def verify_cell_bias_increment(robot, cell):
    """
    If the bot can dig, we add a digging bias to the cell so that it isn't
    tagged as digged by an enemy.
    """
    if robot.nearby(cell):
        cell.increment_digging_bias()


def generate_radar_pos(game, round):
    """
    Generates a random safe position
    """
    global placed_radars_list

    # Initializing variables
    round_bias = get_bias(round)
    rand_x_min, rand_x_max = 4, 10
    rand_y_min, rand_y_max = 4, 10
    max_nb_attempts = 4
    min_dist = 5

    while min_dist > 0:
        attempt = 0
        while attempt < max_nb_attempts:
            bad_position = False
            new_pos = Pos(randint(rand_x_min+round_bias, rand_x_max+round_bias), randint(rand_y_min, rand_y_max))
            dist_list = []

            for radar in placed_radars_list:
                dist = radar.distance(new_pos)
                if dist < min_dist:  # the position is too close to existing riendly radars
                    bad_position = True
                    attempt += 1
                    break
                else:
                    dist_list.append(dist)

            if not bad_position:  # if the position is selected, we check if it's safe
                cell = game.grid.get_cell(new_pos.x, new_pos.y)
                if not cell.is_trapped():
                    return new_pos
                else:
                    attempt += 1

        min_dist -= 1  # if we get here it means that we need to lower the min_dist

    # we should find a position, otherwise crash & investigate
    return None


def generate_predefined_pos(game, loop, robot, radar_position):
    """
    Generates a safe position either from the predefined ones, nearby em' or
    randomly
    """
    global predefined_radar_pos
    global placed_radars_list
    global ore_list

    if len(predefined_radar_pos) != 0:  # we still have many good predefined radar positions
        pos = predefined_radar_pos.pop(0)
        cell = game.grid.get_cell(pos.x, pos.y)
        hole_safe = not holed_by_enemy(cell)
        trap_safe = not cell.is_trapped()
        if hole_safe and trap_safe:  # we check if the position is safe
            return pos
        else:  # we generate a nearby position
            return generate_nearby_pos(pos, game, loop)

    else:  # the important radars are already placed
        if ore_list != [] and isinstance(radar_position, Pos) :  # we select the farest ore that we can see if we have just planted a new radar
            for idx, ore in enumerate(ore_list):
                ore_pos = Pos(ore[0], ore[1])
                # if we are here, it means that radar_position can't be None
                if ore_pos.distance(radar_position) == 4:  # we only take ores in vision's border
                    pos = Pos(ore_pos.x, ore_pos.y)

                    for idx, radar in enumerate(placed_radars_list):  # we check that it's far enough from already placed radars
                        if pos.distance(radar) < 3:
                            break

                    if idx == len(placed_radars_list):  # we got our radar position
                        if ore_list[idx][2] == 1:  # we notify that we're going to dig
                            ore_list.pop(idx)
                        else:  # we remove it from the digging possibilities
                            ore_list[idx][2] -= 1
                        return pos
                    else:
                        continue

            else:  # no good ore position was found
                if predefined_radar_pos == []:  # we pick a random one
                    return generate_radar_pos(game, loop)
                else:  # we pick a predefined good one
                    pos = predefined_radar_pos.pop(0)
                    cell = game.grid.get_cell(pos.x, pos.y)
                    hole_safe = not holed_by_enemy(cell)
                    trap_safe = not cell.is_trapped()
                    if hole_safe and trap_safe:  # we check the cell's safety
                        return pos
                    else:  # if unsafe we pick a nearby position
                        return generate_nearby_pos(pos, game, loop)

        # if we have no available ore position
        if predefined_radar_pos != []:
            safe = False
            pos = predefined_radar_pos.pop(0)
            cell = game.grid.get_cell(pos.x, pos.y)
            hole_safe = not holed_by_enemy(cell)
            trap_safe = not cell.is_trapped()
            if hole_safe and trap_safe:
                return pos
            else:  # we generate a nearby position
                return generate_nearby_pos(pos, game, loop)
        else:  # we generate a random position
            return generate_radar_pos(game, loop)
    # not supposed to be here. Better crash & investigate
    return None


def generate_nearby_pos(pos, game, loop):
    """
    Generates a safe position nearby the given one. If no available one, generates
    a random one
    """
    for x in range(pos.x-1, pos.x+2):
        for y in range(pos.y-1, pos.y+2):
            # we are here if the given position is bad.
            if x != pos.x and y != pos.y and x > 0 and y > -1 and x < 30 and y < 15:
                position = Pos(x, y)
                cell = game.grid.get_cell(x, y)
                hole_safe = not holed_by_enemy(cell)
                trap_safe = not cell.is_trapped()
                if hole_safe and trap_safe:
                    return position

    # if we still haven't yielded anything. We give larger borders
    # we generate the next one or a random one
    for x in range(pos.x-3, pos.x+4):
        for y in range(pos.y-3, pos.y+4):
            # we make sure that we don't go out of the map
            if x != y and x > 0 and y > -1:
                position = Pos(x, y)
                cell = game.grid.get_cell(position.x, position.y)
                hole_safe = not holed_by_enemy(cell)
                trap_safe = not cell.is_trapped()
                if hole_safe and trap_safe:
                    return position
    return generate_radar_pos(game, loop)


def remove_radar_bot(robot):
    """
    Removes the bot from the list of bots responsible of radars
    """
    for idx, bot_id in enumerate(current_radar_bots):
        if bot_id == robot.id:
            current_radar_bots.pop(idx)
            break


def verify_dig_site(game, ore_x, ore_y):
    """
    Verifies if the dig site is trap-free and contains amadeusium.
    """
    dig_cell = game.grid.get_cell(ore_x, ore_y)
    trapped, amadeusium = dig_cell.is_trapped(), dig_cell.get_amadeusium()

    if amadeusium == "?":
        return False
    if int(amadeusium) > 0 and not trapped:
        return True
    return False


def dig_neighboors_or_wait_radar(robot, game, loop, movement_simulation):
    """
    verifies if we should dig neighboors or wait for a radar.
    """
    if verify_not_everyone_digs_neighboors(robot, game):
        dig_neighboors(robot, game, loop)
        return
    else:
        robot.update_status(FREE)
        radar_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation)
        return


def dig_new_ore(robot, game, loop, movement_simulation):
    """
    Picks a new ore for the robot or makes him wait if we find a trap.
    """
    ore_x, ore_y = pick_ore(robot)  # we first select an ore cell

    if ore_x == -1 or ore_y == -1:  # no available ore. We dig the neighbooring cells
        robot.update_status(FREE)
        dig_neighboors_or_wait_radar(robot, game, loop, movement_simulation)
        return
    else:
        cell = game.grid.get_cell(ore_x, ore_y)
        enemy_hole = 1 if holed_by_enemy(cell) else 0
        if not cell.is_trapped() and not enemy_hole:  # safe position
            verify_if_set_trap(robot, game, ore_x, ore_y)
            add_command(robot.dig, ore_x, ore_y, f"{ore_x}, {ore_y}")
            verify_cell_bias_increment(robot, cell)
            robot.update_status(DIGGING, ore_x, ore_y)
        else:  # we wait.
            dig_neighboors_or_wait_radar(robot, game, loop, movement_simulation)
            return


def randomly_stop(robot, threshhold=5):
    """
    Returns true with P(X=True)=threshhold where X ~ U(1, 100).
    We make sure that the bot during his action hasn't already stopped, otherwise
    we return False
    """
    random_value = randint(1, 100)

    if random_value <= threshhold and (not robot.has_already_stopped()) and (robot.item == TRAP or robot.item == RADAR) and robot.x > 4:
        robot.set_already_stopped(True)
        return True
    return False


def debug(message):
    """
    Prints to the error stream
    """
    print(message, file=sys.stderr)


def trap_cell(game, ore_x, ore_y):
    """
    Notifies that the cell has now a friendly trap
    """
    trap = game.grid.get_cell(ore_x, ore_y)
    trap.set_trap()


def radar_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation):
    """
    Makes decisions for the bot if responsible of a radar.
    """
    debug(f"RADAR BOT DECISION FOR BOT: {robot.id}")

    global active_radars_positions
    global placed_radars_list
    global ore_list

    # we get the radar_position associated with this radar bot
    robot_index = robot.id%5
    radar_position = active_radars_positions[robot_index]

    # we explode if we don't have anything valuable and have an advantage
    if robot.item == NONE and len(game.my_robots) >= len(game.enemy_robots):
        for okay_trap in okay_list:
            if robot.nearby(okay_trap):
                x, y = okay_trap.x, okay_trap.y
                add_command(robot.dig, x, y, "kamikaze")
                return

    for juicy_trap in juicy_list:  # we explode on juicy traps whenever we can
        if robot.nearby(juicy_trap):
            x, y = juicy_trap.x, juicy_trap.y
            add_command(robot.dig, x, y, "sayonara")
            return

    x, y = robot.x, robot.y
    if bot_is_free(robot):
        if robot.is_in_HQ():
            if game.radar_cooldown == 0:  # requesting radar
                add_command(robot.request, RADAR)
                game.radar_cooldown = -1  # make sure no one else requests it
            else:  # No available radar
                if verify_not_everyone_digs_neighboors(robot, game):  # everyone is already digging around
                    # NB: we still go here if the other bots are digging real ores
                    remove_radar_bot(robot)
                    digger_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation)
                    return
                else:  # we wait for a radar
                    add_command(robot.wait, "waiting radar")
                    return
        else:
            if radar_position is not None:
                # The radar's job is done and becomes a normal bot again
                update_ore_list(game, radar_position)
                remove_radar_bot(robot)
                active_radars_positions[robot_index] = None
                digger_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation)
                return
            else:   # we want to go to the HQ and wait for a radar for later on
                y_HQ = robot.y
                add_command(robot.move, 0, y_HQ, "TO HQ!")
                return

    else:  # Busy radar bot
        if radar_position is not None:  # we know where to plant it
            x, y = radar_position.x, radar_position.y
            radar_cell_is_done = verify_cell_radar(game, x, y)

            if radar_cell_is_done:
                radar_pos = generate_predefined_pos(game, loop, robot, radar_position)
                radar_position = radar_pos
                active_radars_positions[robot_index] = radar_position
                placed_radars_list.append(Pos(radar_pos.x, radar_pos.y))

            else:  # we take the radar position to dig in
                dig_cell = game.grid.get_cell(radar_position.x, radar_position.y)
                if dig_cell.is_trapped():  # we have to reverify that it is not trapped as the game progressed
                    radar_position = generate_nearby_pos(radar_position, game, loop)
                    active_radars_positions[robot_index] = radar_position
                radar_pos = radar_position

            radar_x, radar_y = radar_pos.x, radar_pos.y

        else:  # we generate the radar position for the first time
            radar_pos = generate_predefined_pos(game, loop, robot, radar_position)
            radar_x, radar_y = radar_pos.x, radar_pos.y
            radar_position = radar_pos
            active_radars_positions[robot_index] = radar_position
            placed_radars_list.append(Pos(radar_x, radar_y))

        # we dig / head to the digging site
        cell = game.grid.get_cell(radar_position.x, radar_position.y)
        enemy_hole = 1 if holed_by_enemy(cell) else 0
        if enemy_hole:  # we generate a safe nearby position
            radar_position = generate_nearby_pos(radar_position, game, loop)
            active_radars_positions[robot_index] = radar_position
            radar_x, radar_y = radar_position.x, radar_position.y

        add_command(robot.dig, radar_x, radar_y, f"rad {radar_x}, {radar_y}")
        verify_cell_bias_increment(robot, cell)
        robot.update_status(DIGGING, radar_x, radar_y)


def verify_not_everyone_digs_neighboors(robot, game):
    """
    Verifies that the 4 other bots aren't digging randomly.
    Returns true if we can go
    """
    global PLACING_LIST

    # we check the number of existing diggers
    incrementor = 0
    for bot in game.my_robots:
        if bot.status in PLACING_LIST and bot.id != robot.id:
            incrementor += 1

    # if we have too many diggers, we go wait for a radar
    if incrementor == 4:
        current_radar_bots.append(robot)
        robot.update_status(HQ)
        return False
    return True


def verify_if_set_trap(robot, game, x, y):
    # if we have a trap and are going to dig, we signal the trap

    if robot.item == TRAP and robot.nearby(Pos(x, y)):
        trap_cell(game, x, y)


def digger_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation):
    debug(f"DIGGER BOT DECISION FOR BOT: {robot.id}")
    global list_dead_bots
    global current_radar_bots

    nb_bots = len(game.my_robots)
    nb_dead_bots = len(list_dead_bots)
    nb_bots_alive = nb_bots - nb_dead_bots

    if robot.item == TRAP:
        score, position = simulate_movement_explosions(robot, game, movement_simulation)
        if score >= 0:
            x, y = position.x, position.y
            explosion_cell = game.grid.get_cell(x, y)
            if explosion_cell.is_trapped():
                add_command(robot.wait, "waiting explosion")
                return
            else:
                add_command(robot.dig, x, y, "sayonara")
                verify_if_set_trap(robot, game, x, y)
                return

    if robot.item == TRAP and not robot.get_simulated():
        score, position = three_step_simulation(robot, game, movement_simulation)
        if score >= 0:
            x, y = position.x, position.y
            explosion_cell = game.grid.get_cell(x, y)
            if position.nearby(explosion_cell) and explosion_cell.is_trapped():  # we check if we don't have to move
                add_command(robot.wait, "waiting explosion")
                return
            else:
                add_command(robot.dig, x, y, "sayonara")
                robot.set_simulated(True)
                verify_if_set_trap(robot, game, x, y)
                return

    if robot.item == NONE and len(game.my_robots) >= len(game.enemy_robots):
        # we explode if we don't have anything valuable and have an advantage
        for okay_trap in okay_list:
            if robot.nearby(okay_trap):
                x, y = okay_trap.x, okay_trap.y
                add_command(robot.dig, x, y, "kamikaze")
                return

    for juicy_trap in juicy_list:  # we explode on juicy traps whenever we can
        if robot.nearby(juicy_trap):
            x, y = juicy_trap.x, juicy_trap.y
            add_command(robot.dig, x, y, "sayonara")
            return

    if robot.item == AMADEUSIUM:  # I'm going home
        robot.update_status(HQ)
        y_HQ = robot.y
        add_command(robot.move, 0, y_HQ, "TO HQ!")
        return

    elif ore_list == [] and robot.item == NONE and robot.status != DIGGING:  # waiting for order
        if robot.x == 0:  # we are in base
            if trap_condition(robot, game, ore_list, nb_bots_alive, loop):  # waiting for trap
                add_command(robot.request, TRAP)
                game.trap_cooldown = -1
                return
        dig_neighboors_or_wait_radar(robot, game, loop, movement_simulation)
        return

    elif robot.status in NOT_BUSY:  # New ore found
        if robot.x == 0:  # we are in base
            if trap_condition(robot, game, ore_list, nb_bots_alive, loop):  # waiting for trap
                add_command(robot.request, TRAP)
                game.trap_cooldown = -1
                return

        dig_new_ore(robot, game, loop, movement_simulation)
        return

    elif robot.status == DIGGING:
        if robot.item == AMADEUSIUM:  # we got ore
            robot.update_status(HQ)
            y_HQ = robot.y
            add_command(robot.move, 0, y_HQ, "TO HQ!")
            return

        else:  # We are still heading to the digging point
            ore_x, ore_y = robot.dig_x, robot.dig_y
            if ore_x != -1 and ore_x != -1:  # valid saved digging position
                valid_dig_site = verify_dig_site(game, ore_x, ore_y)
                valid_value = 1 if valid_dig_site else 0

                if valid_dig_site:  # The ore is still available
                    cell = game.grid.get_cell(ore_x, ore_y)
                    enemy_hole = 1 if holed_by_enemy(cell) else 0
                    if enemy_hole or cell.is_trapped():  # unsafe position
                        robot.update_status(FREE)
                        digger_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation)
                        return
                    else:
                        trap_value = 1 if cell.is_trapped() else 0
                        add_command(robot.dig, ore_x, ore_y, f"{ore_x}, {ore_y}")
                        verify_cell_bias_increment(robot, cell)
                        # before returning, we must trap the position if we had
                        # a trap.

                    verify_if_set_trap(robot, game, ore_x, ore_y)
                    return

                else:  # The ore got mined already or is unsafe. We get a new one
                    ore_x, ore_y = pick_ore(robot)
                    cell = game.grid.get_cell(ore_x, ore_y)
                    if ore_x != -1 and ore_y != -1:  # valid position
                        enemy_hole = 1 if holed_by_enemy(cell) else 0
                        if enemy_hole:
                            robot.update_status(FREE)
                            digger_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation)
                            return
                        else:
                            verify_if_set_trap(robot, game, ore_x, ore_y)
                            add_command(robot.dig, ore_x, ore_y, f"{ore_x}, {ore_y}")
                            verify_cell_bias_increment(robot, cell)
                            robot.update_status(DIGGING, ore_x, ore_y)
                            return
                    else:  # we still didn't manage to find a good position.
                        dig_neighboors_or_wait_radar(robot, game, loop, movement_simulation)

            else:  # we need a new digging position
                dig_new_ore(robot, game, loop, movement_simulation)
                return

    elif robot.status == HQ or robot.item == AMADEUSIUM:  # we go deposit
        if robot.x == 0:
            robot.update_status(FREE)
            if trap_condition(robot, game, ore_list, nb_bots_alive, loop):  # waiting for trap
                # we see if we randomly stop to trick the enemy
                add_command(robot.request, TRAP)
                game.trap_cooldown = -1
                return
            else:  # waiting for orders
                add_command(robot.move, 4, robot.y, "out of HQ")
                return
        else:
            y_HQ = robot.y
            add_command(robot.move, 0, y_HQ, "TO HQ!")
            return
    else:
        debug(f"LOGIC PROBLEM FOR ROBOT: {robot.id}")


def trap_condition(robot, game, ore_list, nb_bots_alive, loop):
    """
    Returns true if the conditions to request a trap are met
    """
    if game.trap_cooldown == 0:
        if len(ore_list) < 2:
            robot.set_simulated(True)
            return True

        if((loop > 40 and loop < 160) or loop == 0): # len(ore_list) < 2*nb_bots_alive and
            robot.set_simulated(True)
            return True
    return False


def decision_making(game, loop, commands_list, juicy_list, okay_list, movement_simulation):
    """
    Main decision making tree.
    """
    global list_dead_bots
    global current_radar_bots
    global ore_list


    nb_bots = len(game.my_robots)
    nb_dead_bots = len(list_dead_bots)
    nb_bots_alive = nb_bots - nb_dead_bots

    start = time.time()
    end = time.time()
    for i in range(nb_bots):
        robot = game.my_robots[i]
        # we give the wait order for all dead robots. F
        if (end-start > 0.49):
            debug("TIMEOUT PREVENTION!!!!")
            add_command(robot.wait, f"TIMEOUT PREVENTION")

        elif robot.is_dead():
            if robot.id not in list_dead_bots:
                list_dead_bots.append(robot.id)
                nb_dead_bots = len(list_dead_bots)
                nb_bots_alive = nb_bots - nb_dead_bots
            add_command(robot.wait, f"dead {robot.x}, {robot.y}")
        # We are a digger if we aren't a radar bot, if we are the last man alive, if the game is almost over or if we have a trap.
        # The last condition avoids requesting a radar & losing the trap
        # elif randomly_stop(robot):
        #     add_command(robot.wait, "randomly waiting")

        elif((robot.id not in current_radar_bots) or (nb_bots_alive == 1 and ore_list != []) or loop > 175  or robot.item == TRAP):
            digger_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation)

        else:
            radar_bot_decisions(game, robot, loop, commands_list, juicy_list, okay_list, movement_simulation)

def execute_commands(commands_list):
    """
    Executing all the commands for the bots
    """
    for command in commands_list:
        func = command[0]
        func(*command[1:])

################### GAME LOOP ##########################

loop = -1
while True:
    # Reinitializing variables
    start = time.time()
    commands_list = []
    trap_list = []
    okay_list, juicy_list = [], []  # store interesting traps to detonate
    dead_bots = []
    decision_list = []
    loop += 1


    # Gathering game infos
    game.my_score, game.enemy_score = [int(i) for i in input().split()]
    debug(f"============================= ROUND: {loop} =============================")
    gathering_grid_data(height, width, game, loop)
    entity_count, game.radar_cooldown, game.trap_cooldown = [int(i) for i in input().split()]

    # Updating game infos
    if loop == 0:
        initiate_game(game, entity_count)
        movement_simulation = [[Pos(0, 0), Pos(0, 0)], [Pos(0, 0), Pos(0, 0)], [Pos(0, 0), Pos(0, 0)], [Pos(0, 0), Pos(0, 0)], [Pos(0, 0), Pos(0, 0)]]
    else:
        okay_list, juicy_list, movement_simulation = update_game(game)

    # Selecting radar bots
    select_special_bots(game, loop)

    # Making decisions
    decision_making(game, loop, commands_list, juicy_list, okay_list, movement_simulation)

    # Executing decisions
    execute_commands(commands_list)
