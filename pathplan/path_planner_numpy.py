'''*-----------------------------------------------------------------------*---
                                                          Authors: Jason Ma
                                                          Date   : Feb 11, 2018
    File Name  : path_planner_numpy.py
    Description: Generates path waypoints using numpy. For all images/rasters,
                 it is important to note that this program treats axis 0 as y.
---*-----------------------------------------------------------------------*'''

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

import numpy as np
from PIL import Image
from math import hypot
from utils import plot_path, read_tif

'''[Config vars]------------------------------------------------------------'''
RASTER_FILE = "../images/rand_squares.tif"
HEIGHT_TOL = 3
PATH_SPACING = 0.5

'''[gen_path]------------------------------------------------------------------
  Adjusts waypoints as necessary to place them over surface model in raster,
  and then interpolates values between raster.
  
  surface_raster - raster image containing surface map
  waypoints - list of waypoints to hit with path
  return - list of points in x,y,z coordinates representing revised waypoints
----------------------------------------------------------------------------'''
def gen_path(surface_raster, waypoints):

  #path_points = []
  x_points = []
  y_points = []
  z_points = []

  if len(waypoints) < 2:
    return path_points

  for i in range(len(waypoints) - 1):
    x, y, z = gen_segment(surface_raster, waypoints[i], waypoints[i + 1])
    x_points.extend(x)
    y_points.extend(y)
    z_points.extend(z)
    #path_points.extend(gen_segment(surface_raster, waypoints[i], waypoints[i + 1]))

  return x_points, y_points, z_points

'''[gen_segment]---------------------------------------------------------------
  Creates a segment from the x and y coordinates in the raster.
  
  surface_raster - raster image containing surface map
  wp0 - source waypoint
  wp1 - dest waypoint
  return - list of x, y, z points interpolated between two waypoints
----------------------------------------------------------------------------'''
def gen_segment(surface_raster, wp0, wp1):
  src_x = wp0[0]
  src_y = wp0[1]

  dest_x = wp1[0]
  dest_y = wp1[1]

  delta_x = dest_x - src_x
  delta_y = dest_y - src_y
  seg_dist = hypot(delta_x, delta_y)

  # Find all points in between src and dest
  # This will be needed when smoothing based on heights!
  #cells = raster_line(wp0, wp1)
  #iterate over points, delete sides if both are lower, repeat if sides deleted

  curr_dist = 0
  x = src_x
  y = src_y

  x_points = []
  y_points = []
  z_points = []
  #points = []

  while curr_dist < seg_dist:
    # calculate avoid height (can also utilize bare earth model in future)
    avoid_height = HEIGHT_TOL

    # stay the designated height above the surface model
    x_points.append(x)
    y_points.append(y)
    z_points.append(surface_raster[int(y)][int(x)] + avoid_height)
    #points.append([x, y, surface_raster[int(y)][int(x)] + avoid_height])

    x += delta_x * PATH_SPACING / seg_dist
    y += delta_y * PATH_SPACING / seg_dist
    curr_dist += PATH_SPACING

  # calculate avoid height
  avoid_height = HEIGHT_TOL
  
  x_points.append(dest_x)
  y_points.append(dest_y)
  z_points.append(surface_raster[int(dest_y)][int(dest_x)] + avoid_height)
  #points.append([dest_x, dest_y, surface_raster[int(dest_y)][int(dest_x)] + avoid_height])

  return x_points, y_points, z_points

'''[raster_line]---------------------------------------------------------------
  Find all raster coordinates that are on path between two waypoints
  
  wp0 - source waypoint
  wp1 - dest waypoint
  return - list of coordinates between two waypoints
----------------------------------------------------------------------------'''
def raster_line(wp0, wp1):

  # start and end coords
  src_x = wp0[0]
  src_y = wp0[1]

  dest_x = wp1[0]
  dest_y = wp1[1]

  # deltas
  dx = dest_x - src_x
  dy = dest_y - src_y

  # sign of movement
  sx = -1 if src_x > dest_x else 1
  sy = -1 if src_y > dest_y else 1

  dx = abs(dx)
  dy = abs(dy)
  
  points = []

  x = src_x
  y = src_y

  ix = 0
  iy = 0

  points.append([x, y])

  while ix < dx or iy < dy:
    # horizontal step
    if (ix + 0.5) / dx < (iy + 0.5) / dy:
      x += sx
      ix += 1
    # vertical step
    else:
      y += sy
      iy += 1
    points.append([x, y])

  return points

'''[smooth_line]---------------------------------------------------------------
  Smoothes a list of point tuples by gradually changing height for sharp
  height changes. The output should also be able to avoid the same obstacles
  that the original path avoids.

  points - original points list
  max_height_diff - max height diff that can occur between two points
  return - list of smoothed points
----------------------------------------------------------------------------'''
def smooth_line(points, max_height_diff):

  #determine peaks of height list and calculate slopes to last peak
  # start at end slope and iterate backwards,
  #   for any slope that is greater than desired, correct heights forwards
  print(points)

  peaks = []
  peak_inds = []
  slopes = []

  #init state
  #last_peak = 0
  going_up = False
  peaks.append(points[0])
  peak_inds.append(0)

  for i in range(1, len(points) - 1):
    z = points[i]
    #going up
    if z > points[i - 1]:
      #last peak is not actually peak
      if going_up:
        peaks.pop()
        peak_inds.pop()
        peaks.append(points[i])
        peak_inds.append(i)
        #last_peak = i
      else:
        going_up = True
        peaks.append(points[i])
        peak_inds.append(i)
        #last_peak = i
    #going down
    else:
      going_up = False

  peaks.append(points[len(points) - 1])
  peak_inds.append(len(points) - 1)
  
  print("Peaks:", peaks)
  print("Peak Inds:", peak_inds)
  
  #peaks seems pretty useless actually...
  for i in range(1, len(peaks)):
    slope = (peaks[i] - peaks[i - 1]) / (peak_inds[i] - peak_inds[i - 1])
    slopes.append(slope)
  
  print("Slopes:", slopes)
  
  # smooth negative slopes
  for i in range(len(slopes)):
    if slopes[i] >= 0:
      continue

    peak_ind_0 = peak_inds[i]
    peak_ind_1 = peak_inds[i + 1]

    for j in range(peak_ind_0 + 1, peak_ind_1 + 1):
      #make all points on this slope neg max_height_diff
      if slopes[i] < max_height_diff * -1:
        #ensure this point is still above terrain
        if points[j - 1] - max_height_diff > points[j]:
          points[j] = points[j - 1] - max_height_diff
      else:
        #ensure this point is still above terrain
        if points[j - 1] + slopes[i] > points[j]:
          points[j] = points[j - 1] + slopes[i]

  
  # smooth positive slopes
  for i in reversed(range(len(slopes))):
    if slopes[i] <= 0:
      continue

    peak_ind_0 = peak_inds[i]
    peak_ind_1 = peak_inds[i + 1]
    #print(peak_ind_0, peak_ind_1)

    for j in reversed(range(peak_ind_0, peak_ind_1)):
      #make all points on this slope max_height_diff
      if slopes[i] > max_height_diff:
        #ensure this point is still above terrain
        if points[j + 1] + max_height_diff > points[j]:
          points[j] = points[j + 1] + max_height_diff
      else:
        #ensure this point is still above terrain
        if points[j + 1] - slopes[i] > points[j]:
          points[j] = points[j + 1] - slopes[i]
  
  return points

'''[read_tif]------------------------------------------------------------------
  Reads tif image into numpy array
  
  filename - filename of tif image
  return - numpy array containing elevation map
----------------------------------------------------------------------------'''
def read_tif(filename):
  #image = Image.open(filename)
  #image = np.array(image)
  #image = plt.imread(filename)
  #i_w = image.shape[0]
  #i_h = image.shape[1]
  #image = image.flatten().reshape((i_w, i_h))
  image = Image.open(filename).convert('L')
  image = np.array(image)
  return image

'''[display_path]--------------------------------------------------------------
  Visualizes path over surface map
  
  packed_waypoints - 1 list for each dimension of waypoints (x,y,z)
  image - raster image containing surface map
  small - whether to only show part of image relevant to path
  return - numpy array containing elevation map
----------------------------------------------------------------------------'''
def display_path(packed_waypoints, image, small=True):
  x_points, y_points, z_points = packed_waypoints

  fig = plt.figure()
  ax = fig.add_subplot(111, projection='3d')
  ax.plot(x_points, y_points, zs=z_points)

  if small:
    max_x = max(x_points)
    max_y = max(y_points)
    print(max_x, max_y)
    print(image[0:max_y+1, 0:max_x+1].shape)

    x_raster = np.arange(0, max_x + 1, step=1)
    y_raster = np.arange(0, max_y + 1, step=1)
    x_raster, y_raster = np.meshgrid(x_raster, y_raster)
    ax.plot_surface(x_raster, y_raster, image[0:max_y+1, 0:max_x+1], cmap=cm.coolwarm,linewidth=0, antialiased=False)
  else:
    x_raster = np.arange(0, image.shape[1], step=1)
    y_raster = np.arange(0, image.shape[0], step=1)
    x_raster, y_raster = np.meshgrid(x_raster, y_raster)
    ax.plot_surface(x_raster, y_raster, image, cmap=cm.coolwarm,linewidth=0, antialiased=False)
  
  plt.show()

'''[main]----------------------------------------------------------------------
  Drives program, reads image in, uses waypoints to generate path, and writes
  path to json file.
----------------------------------------------------------------------------'''
def main():
  image = read_tif(RASTER_FILE)

  #[TODO] read waypoints from file
  waypoints = [(0, 0), (199, 199), (0, 199), (199, 0)]

  #[TODO] possibly do some command line args

  #[TODO] make some gps->raster and raster->gps coord functions

  #[DEBUG]
  #plt.imshow(image)
  #plt.show()
  #print(image)
  #print(image.shape)

  packed_waypoints = gen_path(image, waypoints)
  x, y, z = packed_waypoints
  z = smooth_line(z, 0.5)
  packed_waypoints = x, y, z
  display_path(packed_waypoints, image)

  #[DEBUG]
  #print(raster_line([0,0], [1,7]))
  #smooth_line([3, 2, 3, 4, 2, 1, 3, 2, 5], 3)
  #print()
  #smooth_line([0, 0, 0, 0, 0, 0, 10, 0], 3)

if __name__ == '__main__':
  main()