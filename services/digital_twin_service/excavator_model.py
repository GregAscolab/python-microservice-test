import math

# --- Coordinate System Documentation ---
# The 3D coordinate system is defined as follows:
# - The origin (0, 0, 0) is at the center of the chassis, on the ground.
# - X-axis: Points forward from the chassis.
# - Y-axis: Points to the left of the chassis.
# - Z-axis: Points upwards (height).
#
# Angles:
# - All angles are measured in degrees.
# - Turret angle: Rotation around the Z-axis. 0 degrees is facing forward (along the X-axis). Positive is counter-clockwise.
# - Part angles (Boom, Jib, Bucket): Rotation around the Y-axis (pitch). 0 degrees is horizontal (parallel to the X-Y plane). Positive is upwards.

class Part:
    """
    Represents a single mechanical part in the excavator's kinematic chain.
    """
    def __init__(self, name, settings, parent=None):
        self.name = name
        self.parent = parent

        # --- Dimension Settings Documentation ---
        # 'length': The distance between the start pivot point and the end pivot point of the part.
        # 'offset': An [x, y, z] translation from the parent's end point to this part's start point.
        #           This is useful for parts that are not directly connected at the same pivot.
        self.dimensions = settings.get("dimensions", {})
        self.length = self.dimensions.get("length", 0)
        self.offset = self.dimensions.get("offset", [0, 0, 0])

        self.angle = 0  # The part's current angle in degrees.
        self.start_point = [0, 0, 0]
        self.end_point = [0, 0, 0]

    def update_kinematics(self, parent_end_point=[0, 0, 0], parent_angle=0):
        """
        Calculates the start and end points of this part in the global 3D reference.
        """
        # The start point is the parent's end point plus any offset.
        self.start_point = [
            parent_end_point[0] + self.offset[0],
            parent_end_point[1] + self.offset[1],
            parent_end_point[2] + self.offset[2]
        ]

        # The total angle is the sum of the parent's angle and this part's angle.
        total_angle_rad = math.radians(parent_angle + self.angle)

        # Calculate the end point based on the start point, length, and angle.
        self.end_point = [
            self.start_point[0] + self.length * math.cos(total_angle_rad),
            self.start_point[1], # No change in Y for pitch
            self.start_point[2] + self.length * math.sin(total_angle_rad)
        ]

    def get_height(self):
        """Returns the maximum height (Z coordinate) of the part."""
        return max(self.start_point[2], self.end_point[2])

    def get_radius(self):
        """Returns the horizontal distance (in the X-Y plane) of the part's end point from the origin."""
        return math.sqrt(self.end_point[0]**2 + self.end_point[1]**2)

class Cylinder:
    """
    Represents a hydraulic cylinder. It doesn't have a kinematic representation in this version,
    but stores pressure data and dimensions.
    """
    def __init__(self, name, settings):
        self.name = name

        # --- Dimension Settings Documentation ---
        # 'length': The cylinder's fully retracted length.
        # 'external_diameter': The outer diameter of the cylinder body.
        # 'rod_diameter': The diameter of the cylinder's piston rod.
        self.dimensions = settings.get("dimensions", {})

        self.hp_pressure = 0  # High Pressure
        self.bp_pressure = 0  # Low Pressure

class Excavator:
    def __init__(self, settings, signal_mapping):
        self.signal_mapping = signal_mapping

        # Create the parts in a kinematic chain
        self.chassis = Part("chassis", settings.get("chassis", {}))
        self.turret = Part("turret", settings.get("turret", {}), parent=self.chassis)
        self.boom = Part("boom", settings.get("boom", {}), parent=self.turret)
        self.jib = Part("jib", settings.get("jib", {}), parent=self.boom)
        self.bucket = Part("bucket", settings.get("bucket", {}), parent=self.jib)

        self.parts = [self.chassis, self.turret, self.boom, self.jib, self.bucket]

        # Create the cylinders
        self.boom_cylinder = Cylinder("boom_cylinder", settings.get("boom_cylinder", {}))
        self.jib_cylinder = Cylinder("jib_cylinder", settings.get("jib_cylinder", {}))
        self.bucket_cylinder = Cylinder("bucket_cylinder", settings.get("bucket_cylinder", {}))

        self.cylinders = [self.boom_cylinder, self.jib_cylinder, self.bucket_cylinder]

    def update_from_sensors(self, sensor_state):
        """
        Updates the state of all excavator components from the full sensor state dictionary.
        """
        # Update part angles
        self.chassis.angle = sensor_state.get(self.signal_mapping.get("chassis_slope"), 0)
        self.turret.angle = sensor_state.get(self.signal_mapping.get("turret_angle"), 0)
        self.boom.angle = sensor_state.get(self.signal_mapping.get("boom_angle"), 0)
        self.jib.angle = sensor_state.get(self.signal_mapping.get("jib_angle"), 0)
        self.bucket.angle = sensor_state.get(self.signal_mapping.get("bucket_angle"), 0)

        # Update cylinder pressures
        self.boom_cylinder.hp_pressure = sensor_state.get(self.signal_mapping.get("boom_hp"), 0)
        self.boom_cylinder.bp_pressure = sensor_state.get(self.signal_mapping.get("boom_bp"), 0)
        self.jib_cylinder.hp_pressure = sensor_state.get(self.signal_mapping.get("jib_hp"), 0)
        self.jib_cylinder.bp_pressure = sensor_state.get(self.signal_mapping.get("jib_bp"), 0)
        self.bucket_cylinder.hp_pressure = sensor_state.get(self.signal_mapping.get("bucket_hp"), 0)
        self.bucket_cylinder.bp_pressure = sensor_state.get(self.signal_mapping.get("bucket_bp"), 0)

        # Update the kinematic chain
        self._update_all_kinematics()

    def _update_all_kinematics(self):
        """
        Iterates through the kinematic chain and updates the position of each part.
        """
        parent_end_point = [0, 0, 0]
        parent_angle = 0

        # Special handling for Turret rotation (around Z-axis)
        turret_angle_rad = math.radians(self.turret.angle)

        # Update chassis and turret first (as they are the base)
        self.chassis.update_kinematics()
        self.turret.update_kinematics(self.chassis.end_point)

        # Now update the rest of the parts, which are affected by the turret's rotation
        current_parent_end_point = self.turret.end_point
        current_parent_angle = 0 # Pitch angles start from the turret

        for part in [self.boom, self.jib, self.bucket]:
            part.update_kinematics(current_parent_end_point, current_parent_angle)

            # Apply turret rotation to the calculated end point
            x, y, z = part.end_point
            x_start, y_start, z_start = part.start_point

            # Rotate start and end points around the turret's pivot
            rotated_start_x = x_start * math.cos(turret_angle_rad) - y_start * math.sin(turret_angle_rad)
            rotated_start_y = x_start * math.sin(turret_angle_rad) + y_start * math.cos(turret_angle_rad)
            part.start_point = [rotated_start_x, rotated_start_y, z_start]

            rotated_end_x = x * math.cos(turret_angle_rad) - y * math.sin(turret_angle_rad)
            rotated_end_y = x * math.sin(turret_angle_rad) + y * math.cos(turret_angle_rad)
            part.end_point = [rotated_end_x, rotated_end_y, z]

            current_parent_end_point = part.end_point
            current_parent_angle += part.angle

    def get_3d_representation(self):
        """
        Collects the start and end points of each part for 3D visualization.
        """
        representation = {}
        for part in self.parts:
            representation[part.name] = [part.start_point, part.end_point]
        return representation

    def get_height(self):
        """Returns the maximum height of the bucket."""
        return self.bucket.get_height()

    def get_radius(self):
        """Returns the horizontal radius of the bucket."""
        return self.bucket.get_radius()
