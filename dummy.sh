#!/bin/bash

d() {
    python3 dummy.py $1 $2 $3
}

d 0 1 | d 1 2 1 | d 1 3 2 | d 1 4 3 | d 0 5 4 && d 0 6 | d 0 7 1 || d 0 8 || d 0 9 || d 0 10 || d 0 11 && d 0 12 || d 1 13
