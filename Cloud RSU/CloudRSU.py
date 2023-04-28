import glob
import os
import sys

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

NPC_VEH_NUM = 30
RANGE_CONE = 10
RANGE_RSU = 50
VISUALIZE_CONSTRUCTION_ZONE = True
VISUALIZE_RSU_ZONE = True
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
            nonactive_work_zones, spawn_points

        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        world = client.get_world()
        tm = client.get_trafficmanager(8000)
        blueprint_library = world.get_blueprint_library()
        spawn_points = world.get_map().get_spawn_points()
    except:
        print('Error in initialization')
        destroy()
        exit(1)


def destroy():
    for actor in actor_list:
        actor.destroy()
    print('All actors destroyed')


def construct_work_zone():
    global actor_list, last_communication_time, last_visualize_workzone_time
    cone_bp = blueprint_library.find('static.prop.trafficcone01')
    # coordinate = [[[x,y,yaw], ...]
    coordinates = [[[5, 136, 0], [5, 139, 0], [0, 139, 0], [-5, 136, 0], [-5, 138, 0]]]
    for zone in coordinates:
        cone_list = []
        for coord in zone:
            cone_list.append(world.spawn_actor(cone_bp, carla.Transform(carla.Location(
                x=coord[0], y=coord[1], z=0), carla.Rotation(yaw=coord[2]))))
        actor_list += cone_list
        new_work_zone = wz.WorkZone(cone_list, zone, {}, None, RANGE_CONE, RANGE_RSU)
        active_work_zones.append(new_work_zone)
    print('Work zone constructed')
    last_visualize_workzone_time = time.time()
    last_communication_time = time.time()


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
        tm.distance_to_leading_vehicle(vehicle_i,5.0)
        tm.auto_lane_change(vehicle_i, True)



def visualize_work_zone():
    global last_visualize_workzone_time
    if time.time() - last_visualize_workzone_time < 10:
        return
    if VISUALIZE_CONSTRUCTION_ZONE:
        print('Visualizing work zone')
        for zone in active_work_zones:
            # always display detection area of each cone
            height = 0.6
            detect_range = zone.range_cone
            for cone in zone.cone_coords:
                corner_0 = carla.Location(x=cone[0] + detect_range / 2, y=cone[1] + detect_range / 2, z=height)
                corner_1 = carla.Location(x=cone[0] + detect_range / 2, y=cone[1] - detect_range / 2, z=height)
                corner_2 = carla.Location(x=cone[0] - detect_range / 2, y=cone[1] - detect_range / 2, z=height)
                corner_3 = carla.Location(x=cone[0] - detect_range / 2, y=cone[1] + detect_range / 2, z=height)
                world.debug.draw_line(begin=corner_0, end=corner_1, thickness= 0.02,
                                          color=carla.Color(r=255, g=255, b=0), life_time=10)
                world.debug.draw_line(begin=corner_1, end=corner_2, thickness= 0.02,
                                            color=carla.Color(r=255, g=255, b=0), life_time=10)
                world.debug.draw_line(begin=corner_2, end=corner_3, thickness= 0.02,
                                            color=carla.Color(r=255, g=255, b=0), life_time=10)
                world.debug.draw_line(begin=corner_3, end=corner_0, thickness= 0.02,
                                            color=carla.Color(r=255, g=255, b=0), life_time=10)

            if zone.get_rsu_status():
                display_rsu_range(zone)

        for zone in nonactive_work_zones:
            if zone.get_rsu_status():
                display_rsu_range(zone)
        last_visualize_workzone_time = time.time()


def display_rsu_range(zone):
    # TODO display RSU range
    pass


def work_zone():
    for i in range(len(vehicle_list)-1,-1,-1): # iterate from the last element
        car = vehicle_list[i]
        if not car.is_alive:
            vehicle_list.remove(car)
            continue

        for zone in active_work_zones:
            if is_in_work_zone(car, zone):
                zone.add_car(i)
                # Navigate lane change
                # check to use x or y to compare by compare cone[0] and cone [-2]'s y
                # if y is the same, use x, otherwise use y to compare
                # get the distance between car and the last two cone
                # if it is in the middle (opposite sign), then lane change to the closer cone
                # direction
                # if it distances have same sign, then let it go
                print(f"current zone passed {zone.get_car_num()} cars")
                break



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
        if (car_x - cone_x)**2 + (car_y - cone_y)**2 < zone.range_cone**2:
            if time.time() - last_communication_time > 0.5:
                world.debug.draw_line(begin=cone_loc, end=car_loc, thickness= 0.02,
                                            color=carla.Color(r=255, g=255, b=0), life_time=0.5)
            if abs(car.get_transform().rotation.yaw) - cone_coords[0][2] < 1:
                print(f"car {car.id} is in work zone, with x: {car_x}, y: {car_y}, "
                      f"yaw: {car.get_transform().rotation.yaw}, distance to left cone: "
                      f"{car_y - cone_coords[-2][1]}, distance to right cone: "
                      f"{car_y - cone_coords[-1][1]}")

                return True

if __name__ == '__main__':
    initialize()
    construct_work_zone()
    generate_npc_vehicle()
    while True:
        visualize_work_zone()
        work_zone()
