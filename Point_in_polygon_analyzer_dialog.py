# -*- coding: utf-8 -*- 
"""
/***************************************************************************
 PointInPolygonsDialog
                                 A QGIS plugin
 The plugin shows points within a boundary
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-11-30
        copyright            : (C) 2024 by Samuel Njoka
        email                : bsc-com_09-20@unima.ac.mw
 ***************************************************************************/
"""

import os
import logging
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.core import (QgsVectorLayer, QgsFeature, QgsGeometry, QgsProject, QgsField)
from qgis.PyQt.QtCore import QVariant

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'Point_in_polygon_analyzer_dialog_base.ui'))

class DatabaseHandler:
    """Handles database connections and data submission."""
    def __init__(self, db_name, user, password, host, port):
        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.connection = None

    def connect(self):
        """Establish a connection to the database."""
        import psycopg2
        try:
            self.connection = psycopg2.connect(
                dbname=self.db_name,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            logging.info("Database connection established.")
            return True
        except Exception as e:
            QMessageBox.critical(None, "Database Connection Error", f"Could not connect to database: {str(e)}")
            logging.error(f"Database connection error: {str(e)}")
            return False

    def submit_points(self, points_inside):
        """Submit points inside polygons to the database."""
        if not self.connection:
            logging.warning("No database connection established.")
            return
        
        cursor = self.connection.cursor()
        try:
            for feature in points_inside:
                point_id = feature.id()
                boundary_id = feature['polygon_id']  # Ensure 'polygon_id' is used correctly

                # Ensure the point_id and boundary_id are valid before submission
                if point_id is not None and boundary_id is not None:
                    cursor.execute(
                        "INSERT INTO public.results (point_id, boundary_id, status) "
                        "VALUES (%s, %s, 'inside')",
                        (point_id, boundary_id)
                    )
                    logging.info(f"Submitted point ID {point_id} with boundary ID {boundary_id}.")
            self.connection.commit()
            logging.info("Data submitted successfully.")
        except Exception as e:
            self.connection.rollback()
            QMessageBox.critical(None, "Database Submission Error", f"Could not submit data: {str(e)}")
            logging.error(f"Database submission error: {str(e)}")
        finally:
            cursor.close()

class PointInPolygonsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(PointInPolygonsDialog, self).__init__(parent)
        self.setupUi(self)

        # Connect buttons to methods
        self.btnSelectPointLayer.clicked.connect(self.select_point_layer)
        self.btnSelectPolygonLayer.clicked.connect(self.select_polygon_layer)
        self.btnAnalyze.clicked.connect(self.analyze_points_in_polygons)

        # Initialize layer variables
        self.point_layer = None
        self.polygon_layer = None
        self.db_handler = DatabaseHandler("gis_project", "postgres", "1902", "localhost", "5432")

    def select_point_layer(self):
        """Open file dialog to select point layer."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Point Layer", "", "Shapefile (*.shp);;GeoJSON (*.geojson);;All Files (*)")
        
        if file_path:
            try:
                # Load the point layer
                self.point_layer = QgsVectorLayer(file_path, "Point Layer", "ogr")
                
                if not self.point_layer.isValid():
                    raise Exception("Invalid point layer")
                
                # Validate that it's a point layer
                if self.point_layer.geometryType() != 0:  # 0 represents point geometry
                    raise Exception("Selected layer is not a point layer")
                
                # Update label to show selected layer
                self.lblPointLayer.setText(os.path.basename(file_path))
                logging.info(f"Point layer selected: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not load point layer: {str(e)}")
                logging.error(f"Error loading point layer: {str(e)}")

    def select_polygon_layer(self):
        """Open file dialog to select polygon layer."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Polygon Layer", "", "Shapefile (*.shp);;GeoJSON (*.geojson);;All Files (*)")
        
        if file_path:
            try:
                # Load the polygon layer
                self.polygon_layer = QgsVectorLayer(file_path, "Polygon Layer", "ogr")
                
                if not self.polygon_layer.isValid():
                    raise Exception("Invalid polygon layer")
                
                # Validate that it's a polygon layer
                if self.polygon_layer.geometryType() != 2:  # 2 represents polygon geometry
                    raise Exception("Selected layer is not a polygon layer")
                
                # Update label to show selected layer
                self.lblPolygonLayer.setText(os.path.basename(file_path))
                logging.info(f"Polygon layer selected: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not load polygon layer: {str(e)}")
                logging.error(f"Error loading polygon layer: {str(e)}")

    def analyze_points_in_polygons(self):
        """Analyze points within polygons and display results."""
        # Validation checks
        if not self.point_layer:
            QMessageBox.warning(self, "Error", "Please select a point layer first.")
            logging.warning("Point layer not selected.")
            return
        
        if not self.polygon_layer:
            QMessageBox.warning(self, "Error", "Please select a polygon layer first.")
            logging.warning("Polygon layer not selected.")
            return
        
        # Ensure layers have the same CRS (Coordinate Reference System)
        if self.point_layer.crs().authid() != self.polygon_layer.crs().authid():
            reply = QMessageBox.question(
                self, 
                "CRS Mismatch", 
                "Point and polygon layers have different coordinate systems. Do you want to proceed anyway?", 
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                logging.info("User chose not to proceed with different CRS.")
                return
        
        # Perform point-in-polygon analysis
        points_inside = []
        
        # Check if the 'polygon_id' field exists, and add it if not
        if 'polygon_id' not in self.point_layer.fields().names():
            self.point_layer.dataProvider().addAttributes([QgsField("polygon_id", QVariant.Int)])
            self.point_layer.updateFields()
            logging.info("Added 'polygon_id' field to point layer.")

        # Iterate through point features
        for point_feature in self.point_layer.getFeatures():
            point_geom = point_feature.geometry()
            
            # Check if point is inside any polygon
            is_inside = False
            
            # Check against each polygon
            for polygon_feature in self.polygon_layer.getFeatures():
                polygon_geom = polygon_feature.geometry()
                
                # Check if point is within polygon
                if polygon_geom.contains(point_geom):
                    is_inside = True
                    point_feature['polygon_id'] = polygon_feature.id()  # Store polygon ID
                    break
            # If point is inside, add to the list
            if is_inside:
                points_inside.append(point_feature)
        
        # Create a new memory layer to hold points inside polygons
        fields = self.point_layer.fields()  # Use the same fields as the original point layer
        memory_layer = QgsVectorLayer(f"Point?crs={self.point_layer.crs().authid()}", "Points Inside", "memory")
        memory_layer_data_provider = memory_layer.dataProvider()
        memory_layer_data_provider.addAttributes(fields)
        memory_layer.updateFields()

        # Add points inside to the new memory layer
        for feature in points_inside:
            memory_layer_data_provider.addFeature(feature)
        
        # Add the new layer to the map
        QgsProject.instance().addMapLayer(memory_layer)

        # Correctly count the total number of points
        total_points = sum(1 for _ in self.point_layer.getFeatures())

        # Display results
        results_text = (
            f"Total Points: {total_points}\n"
            f"Points Inside Polygons: {len(points_inside)}"
        )
        
        # Submit points to the database
        if self.db_handler.connect():
            self.db_handler.submit_points(points_inside)

        QMessageBox.information(self, "Analysis Results", results_text)
        logging.info("Analysis completed and results displayed.")

# The following line is essential for the plugin to work correctly in QGIS
# It should be placed in the main plugin file to initiate the dialog
# PointInPolygonsDialog().exec_()