#!/usr/bin/env python3
"""
stats.py: compute statistics for a list of numbers in a CSV file
"""

import sys
import math


def read_numbers(filepath):
    """Read numbers from a CSV file (one per line), return list of floats."""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        # Parse each line as a number
        numbers = [float(line.strip()) for line in lines if line.strip()]
        return numbers
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def calculate_stats(numbers):
    """Calculate count, mean, median, and population standard deviation."""
    count = len(numbers)

    if count == 0:
        return {
            'count': 0,
            'mean': 0,
            'median': 0,
            'stddev': 0
        }

    # Count
    stats_dict = {'count': count}

    # Mean
    mean = sum(numbers) / count
    stats_dict['mean'] = mean

    # Median
    sorted_nums = sorted(numbers)
    if count % 2 == 1:
        median = sorted_nums[count // 2]
    else:
        median = (sorted_nums[count // 2 - 1] + sorted_nums[count // 2]) / 2
    stats_dict['median'] = median

    # Population standard deviation (divide by N, not N-1)
    variance = sum((x - mean) ** 2 for x in numbers) / count
    stddev = math.sqrt(variance)
    stats_dict['stddev'] = stddev

    return stats_dict


def main():
    # Check command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python stats.py <file>")
        sys.exit(1)

    filepath = sys.argv[1]

    # Read numbers from file
    numbers = read_numbers(filepath)

    # Calculate statistics
    stats = calculate_stats(numbers)

    # Print results
    print(f"count: {stats['count']}")
    print(f"mean: {stats['mean']}")
    print(f"median: {stats['median']}")
    print(f"stddev: {stats['stddev']}")


if __name__ == '__main__':
    main()
