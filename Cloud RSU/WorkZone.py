class WorkZone:
    def __init__(self, cone_list, cone_coords, vehicle_list, rsu, range_cone, range_rsu):
        """cone_list: list of construction cones instances constructed by carla. The cone 0
                      should specify the yaw of street heading, the last two cones is for detection
                      of left or right lane. The minimum number of cones is 3.
           cone_coord: list of coordinates of the construction cones
           vehicle_list: dictionary of vehicles that passed through the work zone,
           key: vehicle_id, value: vehicle_id
           rsu: RSU instance, None if no RSU is deployed
           range_cone: communication range of the construction cones
           range_rsu: communication range of the virtual RSU"""
        self.cone_list = cone_list
        self.cone_coords = cone_coords
        self.vehicle_list = vehicle_list
        self.rsu = rsu
        self.range_cone = range_cone
        self.range_rsu = range_rsu

    def add_car(self, car_id):
        """Add a car to the vehicle_list"""
        self.vehicle_list[car_id] = car_id

    def clear_all_car(self):
        """Clear all cars from the vehicle_list"""
        self.vehicle_list.clear()

    def get_car_num(self):
        """Get the number of cars in the vehicle_list"""
        return len(self.vehicle_list)

    def clear_cone_list(self):
        """Clear all cones from the cone_list"""
        self.cone_list.clear()

    def set_cone_list(self, cone_list):
        """Set the cone_list"""
        self.cone_list = cone_list

    def set_rsu(self, rsu):
        """Set the rsu"""
        self.rsu = rsu

    def get_rsu_status(self):
        """Get the status of the RSU"""
        return True if self.rsu != None else False

    def clear_rsu(self):
        """Clear the RSU"""
        self.rsu = None

    def get_mean_location(self):
        """Get the mean location of the work zone"""
        x = 0
        y = 0
        for cone in self.cone_coords:
            x += cone[0]
            y += cone[1]
        return [x/len(self.cone_coords), y/len(self.cone_coords)]

