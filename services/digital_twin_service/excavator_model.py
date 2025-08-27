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
        self.width = self.dimensions.get("width", 0)
        self.offset = self.dimensions.get("offset", [0, 0, 0])

        self.yawAngle = 0  # The part's current angle in degrees around z axis.
        self.pitchAngle = 0  # The part's current angle in degrees around y axis.
        self.rollAngle = 0  # The part's current angle in degrees around x axis.
        self.start_point = [0, 0, 0]
        self.end_point = [0, 0, 0]
        self.planEquation = [0, 0, 0, 0]
        self.planPoints = []
        self.planPlotlySurface = []

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
        # total_angle_rad = math.radians(parent_angle + self.angle)
        total_angle_rad = math.radians(self.pitchAngle)

        # Calculate the end point based on the start point, length, and angle.
        self.end_point = [
            self.start_point[0] + self.length * math.cos(total_angle_rad),
            self.start_point[1], # No change in Y for pitch
            self.start_point[2] + self.length * math.sin(total_angle_rad)
        ]

        # Calculate the plan equation
        if self.rollAngle != 0:
            # self.planEquation = self.__calculate_plane_equation_from_angles(self.rollAngle, self.pitchAngle, 0, self.start_point)
            xc = (self.end_point[0] - self.start_point[0]) / 2 + self.start_point[0]
            yc = (self.end_point[1] - self.start_point[1]) / 2 + self.start_point[1]
            zc = (self.end_point[2] - self.start_point[2]) / 2 + self.start_point[2]
            center_point = [xc, yc, zc]

            self.planPoints = self.calculate_plane_points(self.rollAngle, -self.pitchAngle, 0, self.length, self.width, center_point)

    def get_height(self):
        """Returns the maximum height (Z coordinate) of the part."""
        return max(self.start_point[2], self.end_point[2])

    def get_radius(self):
        """Returns the horizontal distance (in the X-Y plane) of the part's end point from the origin."""
        return math.sqrt(self.end_point[0]**2 + self.end_point[1]**2)
    
    def __calculate_plane_equation_from_angles(self, roll_deg, pitch_deg, yaw_deg, point_on_plane):
        """
        Calcule l'équation d'un plan à partir des angles de roulis, de tangage et de lacet,
        et d'un point connu sur le plan.

        L'équation du plan est de la forme ax + by + cz = d.

        Args:
            roll_deg (float): Angle de roulis en degrés.
            pitch_deg (float): Angle de tangage en degrés.
            yaw_deg (float): Angle de lacet en degrés.
            point_on_plane (list or tuple): Coordonnées [x0, y0, z0] d'un point
                                            sur le plan.

        Returns:
            tuple: Les coefficients (a, b, c, d) de l'équation du plan.
        """
        # Convertir les angles de degrés en radians
        roll_rad = math.radians(roll_deg)
        pitch_rad = math.radians(pitch_deg)
        yaw_rad = math.radians(yaw_deg)

        # Créer les matrices de rotation manuellement comme des listes de listes.
        
        # Matrice de rotation autour de l'axe X (roulis)
        R_x = [
            [1, 0, 0],
            [0, math.cos(roll_rad), -math.sin(roll_rad)],
            [0, math.sin(roll_rad), math.cos(roll_rad)]
        ]

        # Matrice de rotation autour de l'axe Y (tangage)
        R_y = [
            [math.cos(pitch_rad), 0, math.sin(pitch_rad)],
            [0, 1, 0],
            [-math.sin(pitch_rad), 0, math.cos(pitch_rad)]
        ]
        
        # Matrice de rotation autour de l'axe Z (lacet)
        R_z = [
            [math.cos(yaw_rad), -math.sin(yaw_rad), 0],
            [math.sin(yaw_rad), math.cos(yaw_rad), 0],
            [0, 0, 1]
        ]

        # Vecteur normal initial (plan horizontal)
        initial_normal = [0, 0, 1]

        # Appliquer les rotations dans l'ordre Z, Y, X.
        # On effectue la multiplication matricielle manuellement.
        
        # Multiplier R_z par le vecteur normal initial
        temp_normal_1 = [0, 0, 0]
        for i in range(3):
            for j in range(3):
                temp_normal_1[i] += R_z[i][j] * initial_normal[j]

        # Multiplier R_y par le vecteur intermédiaire
        temp_normal_2 = [0, 0, 0]
        for i in range(3):
            for j in range(3):
                temp_normal_2[i] += R_y[i][j] * temp_normal_1[j]
                
        # Multiplier R_x par le dernier vecteur intermédiaire
        rotated_normal = [0, 0, 0]
        for i in range(3):
            for j in range(3):
                rotated_normal[i] += R_x[i][j] * temp_normal_2[j]

        # Les coefficients a, b, c sont les composantes du vecteur normal résultant.
        a, b, c = rotated_normal

        # Calculer le coefficient 'd' en utilisant le produit scalaire.
        d = (a * point_on_plane[0] +
            b * point_on_plane[1] +
            c * point_on_plane[2])

        return [a, b, c, d]

    def multiply_matrix_vector(self, matrix, vector):
        """Effectue une multiplication manuelle d'une matrice 3x3 et d'un vecteur 3x1."""
        result = [0, 0, 0]
        for i in range(3):
            for j in range(3):
                result[i] += matrix[i][j] * vector[j]
        return result
    
    def calculate_plane_points(self, roll_deg, pitch_deg, yaw_deg, length, width, center_point):
        """
        Calcule les 4 points d'un plan à partir des angles, des dimensions et du point central.

        Args:
            roll_deg (float): Angle de roulis en degrés.
            pitch_deg (float): Angle de tangage en degrés.
            yaw_deg (float): Angle de lacet en degrés.
            length (float): Longueur du plan (dimension sur l'axe x local).
            width (float): Largeur du plan (dimension sur l'axe y local).
            center_point (list or tuple): Coordonnées [x0, y0, z0] du point central du plan.

        Returns:
            list: Une liste de 4 points, chacun étant une liste [x, y, z].
        """
        # Convertir les angles de degrés en radians
        roll_rad = math.radians(roll_deg)
        pitch_rad = math.radians(pitch_deg)
        yaw_rad = math.radians(yaw_deg)
        
        # Définir les matrices de rotation pour les axes X, Y et Z.
        R_x = [
            [1, 0, 0],
            [0, math.cos(roll_rad), -math.sin(roll_rad)],
            [0, math.sin(roll_rad), math.cos(roll_rad)]
        ]
        R_y = [
            [math.cos(pitch_rad), 0, math.sin(pitch_rad)],
            [0, 1, 0],
            [-math.sin(pitch_rad), 0, math.cos(pitch_rad)]
        ]
        R_z = [
            [math.cos(yaw_rad), -math.sin(yaw_rad), 0],
            [math.sin(yaw_rad), math.cos(yaw_rad), 0],
            [0, 0, 1]
        ]

        # Définir les points de référence dans le repère local du plan (à (0,0,0) avec l'orientation standard)
        half_length = length / 2
        half_width = width / 2
        
        local_points = [
            [-half_length, -half_width, 0],
            [half_length, -half_width, 0],
            [half_length, half_width, 0],
            [-half_length, half_width, 0]
        ]
        
        plane_points = []
        
        for point in local_points:
            # Appliquer les rotations dans l'ordre Z, Y, X
            rotated_point = self.multiply_matrix_vector(R_z, point)
            rotated_point = self.multiply_matrix_vector(R_y, rotated_point)
            rotated_point = self.multiply_matrix_vector(R_x, rotated_point)

            # Appliquer la translation
            final_point = [
                rotated_point[0] + center_point[0],
                rotated_point[1] + center_point[1],
                rotated_point[2] + center_point[2]
            ]
            plane_points.append(final_point)
        
        return plane_points


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
        self.turret = Part("turret", settings.get("turret", {}))
        self.boom = Part("boom", settings.get("boom", {}), parent=self.turret)
        self.jib = Part("jib", settings.get("jib", {}), parent=self.boom)
        self.bucket = Part("bucket", settings.get("bucket", {}), parent=self.jib)

        self.parts = [self.turret, self.boom, self.jib, self.bucket]

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
        self.turret.pitchAngle = sensor_state.get(self.signal_mapping.get("turret_angle_pitch"), 0)
        self.turret.rollAngle = sensor_state.get(self.signal_mapping.get("turret_angle_roll"), 0)
        self.boom.pitchAngle = sensor_state.get(self.signal_mapping.get("boom_angle_pitch"), 0)
        self.boom.rollAngle = sensor_state.get(self.signal_mapping.get("boom_angle_roll"), 0)
        self.jib.pitchAngle = sensor_state.get(self.signal_mapping.get("jib_angle_pitch"), 0)
        self.jib.rollAngle = sensor_state.get(self.signal_mapping.get("jib_angle_roll"), 0)
        self.bucket.pitchAngle = sensor_state.get(self.signal_mapping.get("bucket_angle_pitch"), 0)
        self.bucket.rollAngle = sensor_state.get(self.signal_mapping.get("bucket_angle_roll"), 0)

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
        # Update turret first (as they are the base)
        self.turret.update_kinematics()

        # Now update the rest of the parts, which are affected by the turret's rotation
        current_parent_end_point = self.turret.end_point
        current_parent_angle = self.turret.pitchAngle

        for part in [self.boom, self.jib, self.bucket]:
            part.update_kinematics(current_parent_end_point, current_parent_angle)
            current_parent_end_point = part.end_point
            current_parent_angle += part.pitchAngle

    def get_3d_representation(self):
        """
        Collects the start and end points of each part for 3D visualization.
        """
        representation = {}
        for part in self.parts:
            representation[part.name] = {"points":[part.start_point, part.end_point], "plan": part.planPoints}
        return representation

    def get_height(self):
        """Returns the maximum height of the bucket."""
        return self.bucket.get_height()

    def get_radius(self):
        """Returns the horizontal radius of the bucket."""
        return self.bucket.get_radius()
