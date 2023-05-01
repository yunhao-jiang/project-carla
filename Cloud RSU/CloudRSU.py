import glob
import os
import sys

from pynput import keyboard

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass
import carla

import random
import time
import numpy as np
import math
import WorkZone as wz
from pynput.keyboard import Listener

NPC_VEH_NUM = 20
RANGE_CONE = 40  # radius
RANGE_RSU = 200  # radius
VISUALIZE_CONSTRUCTION_ZONE = True
VISUALIZE_RSU_ZONE = True
RSU_CREATE_LIMIT = 3
COORDINATES = [[[5, 136, 0], [5, 138.5, 0], [0, 138.5, 0], [-5, 136, 0], [-5, 137.5, 0]]]
COUNT_ALL_CAR = False
CREATE_RSU = True
world = None
tm = None
spawn_points = None
blueprint_library = None
actor_list = []
vehicle_list = []
active_work_zones = []
nonactive_work_zones = []
last_visualize_workzone_time = 0
last_communication_time = 0


def initialize():
    try:
        global world, tm, blueprint_library, actor_list, vehicle_list, active_work_zones, \
            nonactive_work_zones, spawn_points, last_visualize_workzone_time, last_communication_time

        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        world = client.get_world()
        tm = client.get_trafficmanager(8000)
        blueprint_library = world.get_blueprint_library()
        spawn_points = world.get_map().get_spawn_points()
        last_visualize_workzone_time = 0
        last_communication_time = 0
    except:
        print('Error in initialization')
        destroy()
        exit(1)


def destroy():
    for actor in actor_list:
        actor.destroy()
    print('All actors destroyed')


def destroy_init():
    existed_actors = world.get_actors()
    for actor in existed_actors:
        if actor.type_id != 'spectator':
            actor.destroy()


def construct_work_zone(coordinates):
    global actor_list
    cone_bp = blueprint_library.find('static.prop.trafficcone01')
    if coordinates is None:
        coordinates = COORDINATES
    else:
        coordinates = [coordinates]
    # coordinate = [[[x,y,yaw], ...]
    # coordinates = [[[5, 136, 0], [5, 138.5, 0], [0, 138.5, 0], [-5, 136, 0], [-5, 137.5, 0]]]
    for zone in coordinates:
        cone_list = []
        for coord in zone:
            cone_list.append(world.spawn_actor(cone_bp, carla.Transform(carla.Location(
                x=coord[0], y=coord[1], z=0), carla.Rotation(yaw=coord[2]))))
        actor_list += cone_list
        new_work_zone = wz.WorkZone(cone_list, zone, {}, None, RANGE_CONE, RANGE_RSU)
        active_work_zones.append(new_work_zone)
    print('Work zone constructed')


def generate_npc_vehicle():
    for i in range(NPC_VEH_NUM):
        vehicle_bp_i = random.choice(blueprint_library.filter('vehicle.*.*'))
        spawn_point_i = spawn_points[i]

        # Spawn the actor
        vehicle_i = world.try_spawn_actor(vehicle_bp_i, spawn_point_i)

        # Append to the actor_list
        if vehicle_i != None:
            actor_list.append(vehicle_i)
            vehicle_list.append(vehicle_i)
    print('%d vehicles are generated' % len(actor_list))
    for vehicle_i in vehicle_list:
        vehicle_i.set_autopilot(True)
        tm.distance_to_leading_vehicle(vehicle_i, 5.0)
        tm.auto_lane_change(vehicle_i, False)


def visualize_work_zone():
    global last_visualize_workzone_time
    if time.time() - last_visualize_workzone_time < 5:
        return
    if VISUALIZE_CONSTRUCTION_ZONE:
        print('Visualizing work zone')
        for zone in active_work_zones:
            # always display detection area of each cone
            for cone_coords in zone.cone_coords:
                display_range(zone, "cone", cone_coords)

            if zone.get_rsu_status():
                display_range(zone, "rsu", zone.get_mean_location())

        for zone in nonactive_work_zones:
            if zone.get_rsu_status():
                display_range(zone, "rsu", zone.get_mean_location())
        last_visualize_workzone_time = time.time()


def display_range(zone, type, coords):
    obj_coords = coords if type == "cone" else zone.get_mean_location()
    detect_range = zone.range_cone if type == "cone" else zone.range_rsu
    height = 0.6
    color = carla.Color(r=255, g=255, b=0) if type == "cone" else carla.Color(r=0, g=255, b=0)
    corner_0 = carla.Location(x=obj_coords[0] + detect_range / 2,
                              y=obj_coords[1] + detect_range / 2, z=height)
    corner_1 = carla.Location(x=obj_coords[0] + detect_range / 2,
                              y=obj_coords[1] - detect_range / 2, z=height)
    corner_2 = carla.Location(x=obj_coords[0] - detect_range / 2,
                              y=obj_coords[1] - detect_range / 2, z=height)
    corner_3 = carla.Location(x=obj_coords[0] - detect_range / 2,
                              y=obj_coords[1] + detect_range / 2, z=height)

    world.debug.draw_line(begin=corner_0, end=corner_1, thickness=0.05,
                          color=color, life_time=5)
    world.debug.draw_line(begin=corner_1, end=corner_2, thickness=0.05,
                          color=color, life_time=5)
    world.debug.draw_line(begin=corner_2, end=corner_3, thickness=0.05,
                          color=color, life_time=5)
    world.debug.draw_line(begin=corner_3, end=corner_0, thickness=0.05,
                          color=color, life_time=5)

    if type == 'rsu':
        # draw orange detect_range /4 area
        corner_0 = carla.Location(x=obj_coords[0] + detect_range / 4,
                                  y=obj_coords[1] + detect_range / 4, z=height)
        corner_1 = carla.Location(x=obj_coords[0] + detect_range / 4,
                                  y=obj_coords[1] - detect_range / 4, z=height)
        corner_2 = carla.Location(x=obj_coords[0] - detect_range / 4,
                                  y=obj_coords[1] - detect_range / 4, z=height)
        corner_3 = carla.Location(x=obj_coords[0] - detect_range / 4,
                                  y=obj_coords[1] + detect_range / 4, z=height)
        world.debug.draw_line(begin=corner_0, end=corner_1, thickness=0.05,
                              color=carla.Color(r=255, g=165, b=0), life_time=5)
        world.debug.draw_line(begin=corner_1, end=corner_2, thickness=0.05,
                              color=carla.Color(r=255, g=165, b=0), life_time=5)
        world.debug.draw_line(begin=corner_2, end=corner_3, thickness=0.05,
                              color=carla.Color(r=255, g=165, b=0), life_time=5)
        world.debug.draw_line(begin=corner_3, end=corner_0, thickness=0.05,
                              color=carla.Color(r=255, g=165, b=0), life_time=5)


def work_zone():
    for i in range(len(vehicle_list) - 1, -1, -1):  # iterate from the last car
        car = vehicle_list[i]
        if not car.is_alive:
            vehicle_list.remove(car)
            continue

        for zone in active_work_zones:

            in_rsu = is_in_rsu_zone(car, zone)
            in_workzone = is_in_work_zone(car, zone)

            if in_rsu:
                navigate_car(car, zone)
                tm.vehicle_percentage_speed_difference(car, 40)

            if in_workzone == "ALL_CAR":
                zone.add_car(i)
                continue

            if in_workzone:
                zone.add_car(i)
                navigate_car(car, zone)
                tm.vehicle_percentage_speed_difference(car, 40)

            if not in_workzone and not in_rsu:
                tm.vehicle_percentage_speed_difference(car, 0)

            if CREATE_RSU and (not zone.get_rsu_status()) and zone.get_car_num() >= \
                    RSU_CREATE_LIMIT:
                print(f"[INFO] create RSU")
                rsu_bp = blueprint_library.find('static.prop.warningconstruction')
                zone_mean_loc = zone.get_mean_location()
                rsu_transform = carla.Transform(carla.Location(x=zone_mean_loc[0],
                                                               y=zone_mean_loc[1], z=6.5),
                                                carla.Rotation(yaw=zone.get_heading()))
                rsu = world.spawn_actor(rsu_bp, rsu_transform)
                zone.set_rsu(rsu)

        for zone in nonactive_work_zones:
            if zone.get_rsu_status and is_in_rsu_zone(car, zone):
                in_workzone = is_in_work_zone(car, zone)
                navigate_car(car, zone)
                if in_workzone or in_workzone == "ALL_CAR":
                    zone.add_car(i)
                    world.debug.draw_string(car.get_location(), "Not Detected", draw_shadow=False,
                                            color=carla.Color(r=255, g=0, b=0), life_time=1.0)
                if zone.get_car_num() >= RSU_CREATE_LIMIT:
                    zone.clear_rsu()
                    zone.clear_all_cars()
                    print(f"[INFO] RSU is destroyed")


def navigate_car(car, zone):
    # check to use x or y to compare by compare cone[0] and cone [-2]'s y
    cone0_coord = zone.cone_coords[0][0:2]
    cone_end_left_coord = zone.cone_coords[-2][0:2]
    cone_end_right_coord = zone.cone_coords[-1][0:2]
    # if y is the same, use y to compare, else use x to compare
    if cone0_coord[1] == cone_end_left_coord[1]:
        # use x to compare
        comp_digit = 1
    else:
        # use y to compare
        comp_digit = 0
    # get the distance between car and the last two cone
    car_coord = car.get_location().x if comp_digit == 0 else car.get_location().y
    cone_left_dist = car_coord - cone_end_left_coord[comp_digit]
    cone_right_dist = car_coord - cone_end_right_coord[comp_digit]
    # if it is in the middle (opposite sign), then lane change to the closer cone direction
    if cone_left_dist * cone_right_dist < 0:
        if abs(cone_left_dist) < abs(cone_right_dist):
            # lane change to left
            tm.force_lane_change(car, False)
            print(f"[INFO] car {car.id} lane change to left, distance to left cone "
                  f"{cone_left_dist}, distance to right cone {cone_right_dist}")
            world.debug.draw_string(car.get_location(), "left", draw_shadow=False,
                                    color=carla.Color(r=255, g=0, b=0), life_time=1)
        else:
            # lane change to right
            tm.force_lane_change(car, True)
            print(f"[INFO] car {car.id} lane change to right, distance to left cone "
                  f"{cone_left_dist}, distance to right cone {cone_right_dist}")
            world.debug.draw_string(car.get_location(), "right", draw_shadow=False,
                                    color=carla.Color(r=255, g=0, b=0), life_time=1)
    # print(f"current zone passed {zone.get_car_num()} cars")


def is_in_work_zone(car, zone):
    global last_communication_time
    car_x = car.get_location().x
    car_y = car.get_location().y
    cone_coords = zone.cone_coords

    for cone in cone_coords:
        cone_x = cone[0]
        cone_y = cone[1]
        cone_loc = carla.Location(x=cone_x, y=cone_y, z=0.6)
        car_loc = carla.Location(x=car_x, y=car_y, z=0.6)

        dist = math.sqrt((car_x - cone_x) ** 2 + (car_y - cone_y) ** 2)
        if dist < zone.range_cone / 2:  # in workzone range
            # if time.time() - last_communication_time > 0.1:
            world.debug.draw_line(begin=cone_loc, end=car_loc, thickness=0.03,
                                  color=carla.Color(r=255, g=255, b=0), life_time=0.04)
            # last_communication_time = time.time()
            if COUNT_ALL_CAR:
                return "ALL_CAR"
            if abs(abs(car.get_transform().rotation.yaw) - zone.get_heading()) < 1:
                # TODO check the absolute value of the yaw angle at previous line
                return True


def is_in_rsu_zone(car, zone):
    if zone.get_rsu_status() is False:
        return False
    car_x = car.get_location().x
    car_y = car.get_location().y
    rsu_coords = zone.get_mean_location()

    dist = np.sqrt(np.square(car_x - rsu_coords[0]) + np.square(car_y - rsu_coords[1]))

    if dist < zone.range_rsu / 2:  # in rsu
        world.debug.draw_line(begin=carla.Location(x=car_x, y=car_y, z=0.6),
                              end=carla.Location(x=rsu_coords[0], y=rsu_coords[1], z=6.5),
                              thickness=0.03, color=carla.Color(r=0, g=255, b=0), life_time=0.04)
        # If the heading is the same and in 1/2 range of the rsu, then return true
        if abs(abs(car.get_transform().rotation.yaw) - zone.get_heading()) < 1 and dist < \
                zone.range_rsu / 4:
            return True


def on_press(key):
    # if g is pressed, pop the first zone from nonactive_work_zones and add it to active_work_zones
    if key.char == 'g':
        if len(nonactive_work_zones) > 0:
            zone = nonactive_work_zones.pop(0)
            cone_coords = zone.cone_coords
            construct_work_zone(cone_coords)
            active_work_zones.append(zone)
            print(f"[INFO] zone is activated")
        else:
            print("[INFO] no more zone to activate")
    # if h is pressed, pop the first zone from active_work_zones and add it to nonactive_work_zones
    if key.char == 'r':
        if len(active_work_zones) > 0:
            zone = active_work_zones.pop(0)
            zone.clear_cone_list()
            nonactive_work_zones.append(zone)
            zone.clear_all_cars()
            print(f"[INFO] zone is deactivated")
        else:
            print("[INFO] no more zone to deactivate")


if __name__ == '__main__':
    import threading

if __name__ == '__main__':
    listener = Listener(on_press=on_press)
    listener_thread = threading.Thread(target=listener.start)
    listener_thread.start()
    initialize()
    destroy_init()
    construct_work_zone(coordinates=None)
    generate_npc_vehicle()
    while True:
        visualize_work_zone()
        work_zone()



