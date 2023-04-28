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

NPC_VEH_NUM = 100
RANGE_CONE = 10
RANGE_RSU = 50
world = None
tm = None
spawn_points = None
blueprint_library = None
actor_list = []
vehicle_list = []
active_work_zones = []
nonactive_work_zones = []


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


def destroy_init():
    existed_actors = world.get_actors()
    for actor in existed_actors:
        actor.destroy()


def construct_work_zone():
    global actor_list
    cone_bp = blueprint_library.find('static.prop.trafficcone01')
    # coordinate = [[[x,y,yaw], ...]
    coordinates = [[[5, 136, 0], [5, 139, 0], [0, 139, 0], [-5, 136, 0], [-5, 138, 0]],
                   [[5, 133, 180]]]
    for zone in coordinates:
        cone_list = []
        cone_coords = zone
        for coord in zone:
            cone_list.append(world.spawn_actor(cone_bp, carla.Transform(carla.Location(
                x=coord[0], y=coord[1], z=0), carla.Rotation(yaw=coord[2]))))
        actor_list += cone_list
        new_work_zone = wz.WorkZone(cone_list, cone_coords, {}, False, RANGE_CONE, RANGE_RSU)
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


if __name__ == '__main__':
    initialize()
    construct_work_zone()
    generate_npc_vehicle()
