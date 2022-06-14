# -*- coding: utf-8 -*-
"""
=========================================================
Program : Measurements/two_parameter_optimization.py
=========================================================

To Do:
    - document
    - test
    - obj code verification
    - save data
    - 3 param  opt.

Test:
    - data from old files and run routine with wait time
    - test run for comms with Labber
    - small test run using system


Summary:
"""
__author__ =  "Sadman Ahmed Shanto"
__date__ = "06/14/2022"
__email__ = "shanto@usc.edu"

import numpy as np
import os, sys
from scipy.optimize import *

class TookTooLong(Warning):
    pass

class MinimizeStopper(object):
    def __init__(self, max_sec=60):
        self.max_sec = max_sec
        self.start = time.time()
    def __call__(self, xk=None):
        elapsed = time.time() - self.start
        if elapsed > self.max_sec:
            warnings.warn("Terminating optimization: time limit reached",
                          TookTooLong)
        else:
            # you might want to report other stuff here
            print("Elapsed: %.3f sec" % elapsed)


class MeasurementOptimizer:

    """Docstring for MeasurementOptimizer. """

    def __init__(self, paramater1, parameter2, constraints1, constraints2, max_steps, objective_function, max_time, init_guess=None, op_algo="Nelder-Mead"):
        """
        :paramater1: tuple: (name, interface, address, parameter string) e.g. ('Keithley 2400 SourceMeter','GPIB','23', 'Source Current')
        :paramater2: tuple: (name, interface, address, parameter string) e.g. ('Keithley 2400 SourceMeter','GPIB','23', 'Source Current')
        :constraints1: tuple: (min,max)
        :constraints2: tuple: (min,max)
        :objective_function: tuple: (name, interface, address, parameter string) e.g. ('Keithley 2400 SourceMeter','GPIB','23', 'Source Current)
        :init_guess: tuple of best starting value for both parameters: (value_param1, value_param2)
        :max_time: float value representing number of seconds
        :op_algo: string of optimization algorithm: e.g. "Newton-CG"
        """

        self._paramater1 = paramater1
        self._parameter2 = parameter2
        self._constraints1 = constraints1
        self._constraints2 = constraints2
        self._max_steps = max_steps
        self._objective_function = objective_function
        self._init_guess = init_guess
        self._max_time = max_time
        self.op_algo = op_algo


    def start_labber_connections(self):
        client = Labber.connectToServer()

        labber_param1 = client.connectToInstrument(self._labber_paramater1[0], dict(interface=self._labber_paramater1[1], address=self._labber_parameter1[2]))
        labber_param2 = client.connectToInstrument(self._labber_paramater2[0], dict(interface=self._labber_paramater2[1], address=self._labber_parameter2[2]))

        labber_param1.startInstrument()
        labber_param2.startInstrument()

        return labber_param1, labber_param2


    def max_objective_function(self, p1v, p2v):
        """
        p1l: Parmater 1 Labber Object
        p1v: Value to set for Parameter 1

        p2l: Parmater 2 Labber Object
        p2v: Value to set for Parameter 2

        objl: Object Function Labber Object
        """
        # set the parameter values
        p1l.setValue(self._paramater1[3],p1v)
        p2l.setValue(self._paramater2[3],p2v)

        #read the objective function value
        objl.readValue() #????

        return -objl

    def min_objective_function(self, p1v, p2v):
        """
        p1l: Parmater 1 Labber Object
        p1v: Value to set for Parameter 1

        p2l: Parmater 2 Labber Object
        p2v: Value to set for Parameter 2

        objl: Object Function Labber Object
        """
        # set the parameter values
        p1l.setValue(self._paramater1[3],p1v)
        p2l.setValue(self._paramater2[3],p2v)

        #read the objective function value
        objl.readValue() #????

        return objl



    def start_optimization_routine(p1l,p2l):
        global p1l, p2l, objl
        # define starting point
        if init_guess != None:
            p1_guess, p2_guess = self._init_guess
        else:
            p1_guess, p2_guess = (self._constraints1[0], self._constraints2[0])

        # bounds, options and constraints
        p1min, p2min = self._constraints1[0], self._constraints2[0]
        p1max, p2max = self._constraints1[1], self._constraints2[1]
        bnds = ((p1min, p1max), (p2min,p2max))
        optns={'disp': True}
        # we can add max iterations as well
        # optns={'disp': True, 'maxiter':max_iters}

        # set up obj function labber drive
        objl = Labber.connectToServer()
        objl = client.connectToInstrument(self._objective_function[0], dict(interface=self._objective_function[1], address=self._objective_function[2]))
        objl.startInstrument()

        optimum_params = minimize(self.max_objective_function, (p1_guess, p2_guess), method = self.op_algo, bounds = bnds, options = optns, callback=MinimizeStopper(1E-3))

        opt_p1 = optimum.x[0]
        opt_p2 = optimum.x[1]
        return opt_p1, opt_p2



    def run(self):
        # connect with Labber drivers
        p1_labber, p2_labber = self.start_labber_connections()

        # call the correct_optimizaton routine
        self.start_optimization_routine(p1_labber, p2_labber)

