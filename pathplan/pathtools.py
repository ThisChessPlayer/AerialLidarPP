"""
Utility functions to allow for computing MSE of expected and actual waypoints
of the path when running through simulation or in real time. This file also
includes functions to add noise to waypoints to test. For example, the
default noise function over a mean of 0 and a std of 1 will give a MSE of
around 1 usually.

NOTE: This file uses Generators, Lists, Numpy Arrays interchangely, but
will do conversions from generators to lists to numpy arrays if necessary.
"""
from mpl_toolkits.mplot3d import Axes3D

import matplotlib.pyplot as plt
import numpy as np
import json

import types


def generator_to_list(array):
    if isinstance(array, types.GeneratorType):
        return list(array)
    return array

def to_np_array(array):
    if not isinstance(array, np.ndarray):
        return np.array(array)
    return array



def read_path_from_json(filepath):
    """
    Parse a json file containing data points for a path. Expects the file
    to have mappings to `longitude`, `latitude`, and `altitude`
    Returns:
        A generator containing all parsed data points (x=lon, y=lat, z=alt)
    """
    X = "longitude"
    Y = "latitude"
    Z = "altitude"

    to_xyz = lambda pt: np.array([pt[X], pt[Y], pt[Z]])
    points = json.load(open(filepath))
    return map(to_xyz, points)

def default_noise(val=0):
    return val + np.random.normal(0, 1.5)

def gen_noise_points_static(waypoints, noise=lambda x: x + np.random.normal(0, 0.00005)):
    """
    Generates a new path by adding a static noise to all points in the
    original path; which is done via generator. This is the current
    preferred way to generate noisy points from our planned path.
    Args:
        waypoints - a list of waypoints with each point a np-array
    """
    for pt in waypoints:
        yield pt + noise(0)

def gen_noise_points(waypoints, noise=default_noise):
    """ [Deprecated]
    For each point in waypoints, generate a new line perpendicular to it
    using point[i] and point[i+1] as the line. Having this line, select
    randomly one of the nonzero values on this line and add it to the 
    original point[i] to generate a new point in space.
    """
    UP = np.array([0, 0, 1]) # altitude is stored in z-coordinate
    waypoints = map(np.array, waypoints)
    past_point = next(waypoints)

    for pt in waypoints:
        line = pt - past_point
        perpendicular = np.cross(line, UP)
        noise_line = perpendicular * noise()
        yield noise_line + past_point
        past_point = pt

    yield past_point


def norm(vec):
    return np.linalg.norm(vec)

def get_dist_between_points(points, scale=1):
    prev = None
    for pt in points:
        if prev is not None:
            yield norm(pt - prev) * scale
        prev = pt

def total_dist(path):
    return sum(get_dist_between_points(path))

def mse(expected, actual):
    """
    Mean squared error of expected and actual waypoints.
    Args:
        expected - A list/generator/np-array of planned waypoints.
        actual - The list/generator/np-array of points that we flew to.
    Returns:
        The mean squared error
    """
    expected = to_np_array(generator_to_list(expected))
    actual = to_np_array(generator_to_list(actual))

    return ((expected - actual)**2).mean(axis=0) # avg along columns

def calc_errors_with_gen_noise(filepath, metric=mse):
    waypoints = list(read_path_from_json(filepath))
    noise_pts = list(gen_noise_points(waypoints))
    return metric(expected=waypoints, actual=noise_pts)

def print_planned_and_flown_path_debug_info(planned, flown, metric=mse):
    print(f"Path Debug:")
    print(f"  len(planned) = {len(planned)}")
    print(f"  len(flown)   = {len(flown)}")
    print(f"  Total distance traveled for planned path: {total_dist(planned)}")
    print(f"  Total distance traveled for flown path: {total_dist(planned)}")
    print(f"  Error based on metric = {metric(planned, flown)}")

def display_two_paths(one, two):
    """
    Args:
        path_one - List of waypoints in format [(x, y, z), (x, y, z), ...]
        path_two - List of waypoints in format [(x, y, z), (x, y, z), ...]
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot(*np.array(one).T, 'k-', color='b', linewidth=1.0)
    ax.plot(*np.array(two).T, 'k-', color='r', linewidth=1.0)
    plt.show()

def display_gen_noise_path_with_file(filepath):
    waypoints = list(read_path_from_json(filepath))
    noise_pts = list(gen_noise_points(waypoints))
    display_two_paths(waypoints, noise_pts)

def display_surface(path_one, path_two):
    """
    Display a graph of the a surface between two paths. Expects the two
    input paths to have the same amount of data points. (ie len(one) == len(two))
    Args:
        path_one - List of waypoints in format [(x, y, z), (x, y, z), ...]
        path_two - List of waypoints in format [(x, y, z), (x, y, z), ...]
    """

    Z1 = 8.0
    Z2 = 9.0

    x1, y1, z1 = np.array(path_one).T
    x2, y2, z2 = np.array(path_two).T

    i, h = np.meshgrid(np.arange(len(x1)), np.linspace(Z1, Z2, 10))
    X = (x2[i] - x1[i]) / (Z2 - Z1) * (h - Z1) + x1[i]
    Y = (y2[i] - y1[i]) / (Z2 - Z1) * (h - Z1) + y1[i]
    Z = (z2[i] - z1[i]) / (Z2 - Z1) * (h - Z1) + z1[i]

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot(x1, y1, z1, 'k-', linewidth=0.3, color='b')
    ax.plot(x2, y2, z2, 'k-', linewidth=0.3, color='m')
    ax.plot_surface(X, Y, Z, color='r', alpha=0.4, linewidth=0)

    plt.show()

def display_surface_with_file(filepath):
    """ 
    Displays a graph of the error surface between input path and a path 
    generated by adding some noise to the input path.

    Args:
        filepath - JSON file containing the path itself
    """
    waypoints = list(read_path_from_json(filepath))
    noise_pts = list(gen_noise_points_static(waypoints))

    display_surface(waypoints, noise_pts)


def main():
    err = calc_errors_with_gen_noise("output/path.json", metric=mse)
    print("MSE={}".format(err))

    # display_gen_noise_path_with_file("path.json")
    display_surface_with_file("output/path.json")

# Uncomment to test
# if __name__ == "__main__":
#     main()