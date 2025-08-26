import math

class Part:
    def __init__(self, name, dimensions):
        self.name = name
        self.dimensions = dimensions
        self.x = 0
        self.y = 0
        self.z = 0
        self.angle = 0

class Chassis(Part):
    def __init__(self, dimensions):
        super().__init__("chassis", dimensions)

class Turret(Part):
    def __init__(self, dimensions):
        super().__init__("turret", dimensions)

class Boom(Part):
    def __init__(self, dimensions):
        super().__init__("boom", dimensions)

class Jib(Part):
    def __init__(self, dimensions):
        super().__init__("jib", dimensions)

class Bucket(Part):
    def __init__(self, dimensions):
        super().__init__("bucket", dimensions)

class Excavator:
    def __init__(self, settings, signal_mapping):
        self.chassis = Chassis(settings.get("chassis", {}))
        self.turret = Turret(settings.get("turret", {}))
        self.boom = Boom(settings.get("boom", {}))
        self.jib = Jib(settings.get("jib", {}))
        self.bucket = Bucket(settings.get("bucket", {}))
        self.signal_mapping = signal_mapping

    def update_from_sensors(self, sensor_state):
        """
        Updates the angles of all excavator parts from the full sensor state dictionary.
        """
        self.chassis.angle = sensor_state.get(self.signal_mapping.get("chassis_slope"), 0)
        self.turret.angle = sensor_state.get(self.signal_mapping.get("turret_angle"), 0)
        self.boom.angle = sensor_state.get(self.signal_mapping.get("boom_angle"), 0)
        self.jib.angle = sensor_state.get(self.signal_mapping.get("jib_angle"), 0)
        self.bucket.angle = sensor_state.get(self.signal_mapping.get("bucket_angle"), 0)

    def get_3d_representation(self):
        """
        Calculates and returns the 3D coordinates of the excavator parts based on the current angles.
        It's assumed that update_from_sensors has been called recently.
        """
        # For simplicity, we'll do the calculations in 2D (x, y) and then map to 3D (x, z)
        # Y in 2D corresponds to height.

        # Chassis
        chassis_x0, chassis_y0 = -self.chassis.dimensions.get("length", 5) / 2, 0
        chassis_x1, chassis_y1 = self.chassis.dimensions.get("length", 5) / 2, 0
        chassis_z = 0

        # Turret
        turret_x = 0
        turret_y = self.chassis.dimensions.get("height", 1)
        turret_z = 0

        # Boom
        boom_length = self.boom.dimensions.get("length", 8)
        boom_angle_rad = math.radians(self.boom.angle)
        boom_x0 = turret_x
        boom_y0 = turret_y
        boom_x1 = boom_x0 + boom_length * math.cos(boom_angle_rad)
        boom_y1 = boom_y0 + boom_length * math.sin(boom_angle_rad)
        boom_z = 0

        # Jib
        jib_length = self.jib.dimensions.get("length", 4)
        # Jib angle is relative to the boom
        jib_angle_rad = math.radians(self.boom.angle + self.jib.angle)
        jib_x0 = boom_x1
        jib_y0 = boom_y1
        jib_x1 = jib_x0 + jib_length * math.cos(jib_angle_rad)
        jib_y1 = jib_y0 + jib_length * math.sin(jib_angle_rad)
        jib_z = 0

        # Bucket
        bucket_x = jib_x1
        bucket_y = jib_y1
        bucket_z = 0

        self._last_3d_representation = {
            "chassis": [[chassis_x0, chassis_z, chassis_y0], [chassis_x1, chassis_z, chassis_y1]],
            "turret": [[turret_x, turret_z, turret_y]],
            "boom": [[boom_x0, boom_z, boom_y0], [boom_x1, boom_z, boom_y1]],
            "jib": [[jib_x0, jib_z, jib_y0], [jib_x1, jib_z, jib_y1]],
            "bucket": [[bucket_x, bucket_z, bucket_y]]
        }
        return self._last_3d_representation

    def get_height(self):
        """
        Returns the height of the bucket from the last calculated 3D representation.
        """
        if hasattr(self, '_last_3d_representation'):
            return self._last_3d_representation["bucket"][0][2]
        return 0

    def get_radius(self):
        """
        Returns the radius of the bucket from the last calculated 3D representation.
        """
        if hasattr(self, '_last_3d_representation'):
            bucket_pos = self._last_3d_representation["bucket"][0]
            turret_pos = self._last_3d_representation["turret"][0]
            return math.sqrt((bucket_pos[0] - turret_pos[0])**2 + (bucket_pos[1] - turret_pos[1])**2)
        return 0
