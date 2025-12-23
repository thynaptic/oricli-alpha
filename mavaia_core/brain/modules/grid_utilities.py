"""
Grid Utilities Module
Shared utilities for grid parsing, validation, and transformations
Used by multiple solver modules (ARC, spatial, etc.)
"""

from typing import Dict, Any, Optional, List, Tuple
import sys
import json
import re
import copy
from collections import deque, Counter


class GridUtilities:
    """Shared utilities for grid operations"""
    
    @staticmethod
    def parse_grid_from_text(text: str) -> Optional[List[List[Any]]]:
        """
        Parse grid from text description
        
        Handles multiple formats:
        - JSON arrays: [[1,2,3],[4,5,6]]
        - Visual representations
        - Text descriptions
        
        Args:
            text: Text containing grid representation
            
        Returns:
            Parsed grid array or None if parsing fails
        """
        # Input validation
        if not text or not isinstance(text, str):
            return None
        
        # Try JSON format first
        try:
            # Look for JSON array pattern
            json_pattern = r'\[\[[\d\s,\[\]]+\]\]'
            matches = re.findall(json_pattern, text)
            if matches:
                grid = json.loads(matches[0])
                if GridUtilities.validate_grid(grid):
                    return grid
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Try nested array pattern without JSON
        try:
            # Pattern: [[1, 2, 3], [4, 5, 6]]
            array_pattern = r'\[\[([^\]]+)\]\]'
            matches = re.findall(array_pattern, text)
            if matches:
                # Parse each row
                grid = []
                for match in matches:
                    # Extract numbers from row
                    numbers = re.findall(r'\d+', match)
                    if numbers:
                        row = [int(n) for n in numbers]
                        grid.append(row)
                
                if grid and GridUtilities.validate_grid(grid):
                    return grid
        except (ValueError, IndexError):
            pass
        
        # Try visual representation (simplified)
        # Look for lines with numbers separated by spaces or commas
        lines = text.split('\n')
        grid = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to extract numbers
            numbers = re.findall(r'\d+', line)
            if numbers:
                row = [int(n) for n in numbers]
                if len(row) > 0:
                    grid.append(row)
        
        if grid and GridUtilities.validate_grid(grid):
            return grid
        
        return None
    
    @staticmethod
    def validate_grid(grid: Any) -> bool:
        """
        Validate grid structure and values
        
        Args:
            grid: Grid to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(grid, list):
            return False
        
        if len(grid) == 0:
            return False
        
        # Check all rows are lists
        if not all(isinstance(row, list) for row in grid):
            return False
        
        # Check all rows have same length
        if len(set(len(row) for row in grid)) > 1:
            return False
        
        # Check all values are numeric (int or float)
        for row in grid:
            for cell in row:
                if not isinstance(cell, (int, float)):
                    return False
        
        return True
    
    @staticmethod
    def apply_translation(grid: List[List[Any]], dx: int, dy: int) -> List[List[Any]]:
        """
        Apply translation to grid
        
        Args:
            grid: Input grid
            dx: Horizontal translation
            dy: Vertical translation
            
        Returns:
            Translated grid
        """
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Create new grid with translated positions
        result = [[0 for _ in range(width)] for _ in range(height)]
        
        for y in range(height):
            for x in range(width):
                if grid[y][x] != 0:
                    new_x = x + dx
                    new_y = y + dy
                    if 0 <= new_y < height and 0 <= new_x < width:
                        result[new_y][new_x] = grid[y][x]
        
        return result
    
    @staticmethod
    def apply_duplication(grid: List[List[Any]], tiles_x: int, tiles_y: int) -> List[List[Any]]:
        """
        Apply duplication/tiling to grid
        
        Args:
            grid: Input grid
            tiles_x: Number of horizontal tiles
            tiles_y: Number of vertical tiles
            
        Returns:
            Tiled grid
        """
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        new_height = height * tiles_y
        new_width = width * tiles_x
        
        result = [[0 for _ in range(new_width)] for _ in range(new_height)]
        
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for y in range(height):
                    for x in range(width):
                        result[ty * height + y][tx * width + x] = grid[y][x]
        
        return result
    
    @staticmethod
    def apply_continuation(grid: List[List[Any]], direction: str, pattern: str) -> List[List[Any]]:
        """
        Apply pattern continuation to grid
        
        Args:
            grid: Input grid
            direction: "right", "down", "left", "up"
            pattern: "linear", "geometric", "periodic"
            
        Returns:
            Grid with continued pattern
        """
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        result = copy.deepcopy(grid)
        
        if direction == "right" and width > 0:
            # Continue pattern to the right
            # Use last column as pattern
            last_col = [grid[y][width - 1] for y in range(height)]
            # Extend grid
            for _ in range(width):  # Double the width
                for y in range(height):
                    result[y].append(last_col[y])
        
        elif direction == "down" and height > 0:
            # Continue pattern downward
            # Use last row as pattern
            last_row = grid[height - 1][:]
            # Extend grid
            for _ in range(height):  # Double the height
                result.append(last_row[:])
        
        # Other directions and patterns would need more sophisticated implementation
        return result
    
    @staticmethod
    def apply_color_mapping(grid: List[List[Any]], 
                            color_mapping: Dict[Any, Any]) -> List[List[Any]]:
        """
        Apply color mapping to grid with pattern inference
        
        Args:
            grid: Input grid
            color_mapping: Dictionary mapping old colors to new colors
        
        Returns:
            Grid with colors mapped
        """
        result = copy.deepcopy(grid)
        
        # Detect pattern in mapping (e.g., all mappings are +1, *2, etc.)
        if color_mapping:
            keys = list(color_mapping.keys())
            values = list(color_mapping.values())
            
            # Check if there's a consistent pattern
            if len(keys) == 1 and len(values) == 1:
                # Single mapping: try to infer pattern
                diff = values[0] - keys[0]
                # Apply pattern to all non-zero cells
                for y in range(len(result)):
                    for x in range(len(result[0])):
                        cell = result[y][x]
                        if cell != 0 and cell not in color_mapping:
                            # Apply inferred pattern
                            result[y][x] = cell + diff
                        elif cell in color_mapping:
                            result[y][x] = color_mapping[cell]
            else:
                # Multiple mappings: apply directly
                for y in range(len(result)):
                    for x in range(len(result[0])):
                        cell = result[y][x]
                        if cell in color_mapping:
                            result[y][x] = color_mapping[cell]
        
        return result
    
    @staticmethod
    def apply_rotation_reflection(grid: List[List[Any]], rotation: int = 0, 
                                  reflection: str = None) -> List[List[Any]]:
        """
        Apply rotation and/or reflection to grid
        
        Args:
            grid: 2D grid
            rotation: Rotation in degrees (0, 90, 180, 270)
            reflection: Reflection type ('horizontal', 'vertical', 'diagonal', None)
        
        Returns:
            Transformed grid
        """
        result = copy.deepcopy(grid)
        
        # Apply rotation
        if rotation == 90:
            # Rotate 90 degrees clockwise
            result = [[result[j][i] for j in range(len(result)-1, -1, -1)] 
                     for i in range(len(result[0]))]
        elif rotation == 180:
            # Rotate 180 degrees
            result = [[result[i][j] for j in range(len(result[0])-1, -1, -1)] 
                     for i in range(len(result)-1, -1, -1)]
        elif rotation == 270:
            # Rotate 270 degrees clockwise (90 counterclockwise)
            result = [[result[j][i] for j in range(len(result))] 
                     for i in range(len(result[0])-1, -1, -1)]
        
        # Apply reflection
        if reflection == 'horizontal':
            # Reflect across horizontal axis (flip vertically)
            result = result[::-1]
        elif reflection == 'vertical':
            # Reflect across vertical axis (flip horizontally)
            result = [row[::-1] for row in result]
        elif reflection == 'diagonal':
            # Reflect across main diagonal
            result = [[result[j][i] for j in range(len(result))] 
                     for i in range(len(result[0]))]
        
        return result
    
    @staticmethod
    def detect_shapes(grid: List[List[Any]]) -> List[Dict[str, Any]]:
        """
        Detect connected components and classify shapes in grid
        
        Uses flood fill to find connected components, then classifies them
        as rectangles, lines, circles, polygons, or irregular shapes.
        
        Args:
            grid: 2D grid array
            
        Returns:
            List of shape dictionaries with type, bounds, cells, properties
        """
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        if width == 0:
            return []
        
        shapes = []
        visited = set()
        
        # Directions for 4-connected and 8-connected
        directions_4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        directions_8 = directions_4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        def flood_fill(start_y: int, start_x: int, value: Any, use_8_connected: bool = True) -> List[Tuple[int, int]]:
            """Flood fill to find connected component"""
            component = []
            queue = deque([(start_y, start_x)])
            visited_local = set()
            dirs = directions_8 if use_8_connected else directions_4
            
            while queue:
                y, x = queue.popleft()
                if (y, x) in visited_local or (y, x) in visited:
                    continue
                if y < 0 or y >= height or x < 0 or x >= width:
                    continue
                if grid[y][x] != value:
                    continue
                
                visited_local.add((y, x))
                visited.add((y, x))
                component.append((x, y))  # Store as (x, y) for consistency
                
                for dy, dx in dirs:
                    ny, nx = y + dy, x + dx
                    if (ny, nx) not in visited_local:
                        queue.append((ny, nx))
            
            return component
        
        # Find all connected components
        for y in range(height):
            for x in range(width):
                if (y, x) not in visited and grid[y][x] != 0:
                    value = grid[y][x]
                    component = flood_fill(y, x, value, use_8_connected=True)
                    
                    if not component:
                        continue
                    
                    # Calculate bounding box
                    xs = [p[0] for p in component]
                    ys = [p[1] for p in component]
                    min_x, max_x = min(xs), max(xs)
                    min_y, max_y = min(ys), max(ys)
                    bbox_width = max_x - min_x + 1
                    bbox_height = max_y - min_y + 1
                    area = len(component)
                    
                    # Calculate centroid
                    centroid_x = sum(xs) / len(xs) if xs else 0
                    centroid_y = sum(ys) / len(ys) if ys else 0
                    
                    # Classify shape
                    shape_type = "irregular"
                    
                    # Check if rectangle (all cells in bounding box are filled)
                    if area == bbox_width * bbox_height:
                        # Check if it's actually a rectangle (all cells have same value)
                        is_rect = True
                        for cy in range(min_y, max_y + 1):
                            for cx in range(min_x, max_x + 1):
                                if grid[cy][cx] != value:
                                    is_rect = False
                                    break
                            if not is_rect:
                                break
                        if is_rect:
                            shape_type = "rectangle"
                    
                    # Check if line (width or height is 1)
                    elif bbox_width == 1 or bbox_height == 1:
                        shape_type = "line"
                        if bbox_width == 1 and bbox_height == 1:
                            shape_type = "point"
                    
                    # Check if circle-like (area close to π * (min_dim/2)^2)
                    elif abs(area - 3.14159 * (min(bbox_width, bbox_height) / 2) ** 2) < area * 0.3:
                        shape_type = "circle"
                    
                    # Check if polygon (convex hull area close to bounding box)
                    else:
                        # Simple heuristic: if area is close to bounding box, it's more rectangular
                        fill_ratio = area / (bbox_width * bbox_height)
                        if fill_ratio > 0.8:
                            shape_type = "polygon"
                    
                    # Calculate perimeter (approximate)
                    perimeter = 0
                    for x, y in component:
                        # Count edges that border empty cells or grid boundaries
                        for dy, dx in directions_4:
                            ny, nx = y + dy, x + dx
                            if ny < 0 or ny >= height or nx < 0 or nx >= width:
                                perimeter += 1
                            elif grid[ny][nx] != value:
                                perimeter += 1
                    
                    shapes.append({
                        "type": shape_type,
                        "value": value,
                        "cells": component,
                        "bounds": {
                            "min_x": min_x,
                            "max_x": max_x,
                            "min_y": min_y,
                            "max_y": max_y,
                            "width": bbox_width,
                            "height": bbox_height
                        },
                        "properties": {
                            "area": area,
                            "perimeter": perimeter,
                            "centroid": (centroid_x, centroid_y),
                            "fill_ratio": area / (bbox_width * bbox_height) if bbox_width * bbox_height > 0 else 0
                        }
                    })
        
        return shapes
    
    @staticmethod
    def detect_adjacency(grid: List[List[Any]]) -> Dict[str, Any]:
        """
        Build adjacency graphs and detect connected regions
        
        Args:
            grid: 2D grid array
            
        Returns:
            Dictionary with adjacency graph and region maps
        """
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Build adjacency graph (4-connected and 8-connected)
        adjacency_4 = {}  # Map (x, y) to list of neighbors (4-connected)
        adjacency_8 = {}  # Map (x, y) to list of neighbors (8-connected)
        
        directions_4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        directions_8 = directions_4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for y in range(height):
            for x in range(width):
                if grid[y][x] != 0:
                    pos = (x, y)
                    adjacency_4[pos] = []
                    adjacency_8[pos] = []
                    
                    for dx, dy in directions_4:
                        nx, ny = x + dx, y + dy
                        if 0 <= ny < height and 0 <= nx < width and grid[ny][nx] != 0:
                            adjacency_4[pos].append((nx, ny))
                    
                    for dx, dy in directions_8:
                        nx, ny = x + dx, y + dy
                        if 0 <= ny < height and 0 <= nx < width and grid[ny][nx] != 0:
                            adjacency_8[pos].append((nx, ny))
        
        # Detect connected regions (using flood fill)
        regions_4 = []  # 4-connected regions
        regions_8 = []  # 8-connected regions
        visited_4 = set()
        visited_8 = set()
        
        def find_region(start_pos: Tuple[int, int], visited: set, adjacency: Dict, region_id: int) -> List[Tuple[int, int]]:
            """Find connected region using BFS"""
            region = []
            queue = deque([start_pos])
            
            while queue:
                pos = queue.popleft()
                if pos in visited:
                    continue
                visited.add(pos)
                region.append(pos)
                
                if pos in adjacency:
                    for neighbor in adjacency[pos]:
                        if neighbor not in visited:
                            queue.append(neighbor)
            
            return region
        
        region_id = 0
        for y in range(height):
            for x in range(width):
                if grid[y][x] != 0:
                    pos = (x, y)
                    if pos not in visited_4:
                        region = find_region(pos, visited_4, adjacency_4, region_id)
                        if region:
                            regions_4.append({
                                "id": region_id,
                                "cells": region,
                                "value": grid[y][x]
                            })
                            region_id += 1
        
        region_id = 0
        for y in range(height):
            for x in range(width):
                if grid[y][x] != 0:
                    pos = (x, y)
                    if pos not in visited_8:
                        region = find_region(pos, visited_8, adjacency_8, region_id)
                        if region:
                            regions_8.append({
                                "id": region_id,
                                "cells": region,
                                "value": grid[y][x]
                            })
                            region_id += 1
        
        # Calculate distances between objects
        distances = {}
        non_zero_positions = [(x, y) for y in range(height) for x in range(width) if grid[y][x] != 0]
        
        for i, (x1, y1) in enumerate(non_zero_positions):
            for j, (x2, y2) in enumerate(non_zero_positions[i+1:], i+1):
                dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                distances[((x1, y1), (x2, y2))] = dist
        
        return {
            "adjacency_4": adjacency_4,
            "adjacency_8": adjacency_8,
            "regions_4": regions_4,
            "regions_8": regions_8,
            "distances": distances
        }

