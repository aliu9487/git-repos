####### Version Note ################
#####################################
'''

Test Git update and download

- draft V1.4
- checkpoint 2019/07/27 4:00 AM
- bugfix: 
	a. stop baseline update while gesture starts
	b. ensure stable gesture start and stop point capture
	c. enable opportunity for Double click and long press gesture 
	(To Be Developed...)

- draft V1.3
- checkpoint 2019/08/25/15:00
- simplified file path access, one click version.
- input file name: rawData.txt
- output file name: Result.txt

- draft V1.2
- checkpoint 2019/08/25/13:30
- try to add features of reading file from external text


- draft V1.1
- checkpoint 2019/08/24/21:40
- This is the first working model for UDLR access. 
- No Double click yet
- No long press yet
- only inner circle sensor is working 
- outer circle sensor needs to wait for mechnical and hardware respin.

'''
#####################################


##########################################################################
################ File system access ######################################
filepath_io = "File_IO_control.txt"
File_IO = open(filepath_io, 'r')

input_path = File_IO.readline()
input_path = input_path[:-1]
# print(input_path)
output_path = File_IO.readline()
output_path = output_path[:-1]
# print(output_path)
log_path = File_IO.readline()
log_path = log_path[:-1]

# print(log_path)

File_IO.close()

debugFile = open('./debugFile.txt', 'w')

InputFile = open(input_path, 'r')
# for debug use
OutputFile = open(output_path, 'w')
LogFile = open(log_path, 'w')
# dataline = InputFile.readline()
lines = 0

print("OutputFile is : " + str(output_path))

###########################################################################
############### Global variable definition ################################


# definition of raw data filter size
RAW_FILTER_SIZE = 6

# definition of baseline filter size
# size set to 60 for 1.5 seconds of data
# assuming AD7146 runs at 40 samples per second
BASELINE_FILTER_SIZE = 60

# definition of sensitivity thresholding (default value 100)
THRESHOLD_POS = 100
THRESHOLD_NEG = -100

# 3 lists of size 6 as a moving average of CDC raw data
S0_RawFilt = []
S1_RawFilt = []
S2_RawFilt = []

# 3 lists of size 60 to store S0,S1,S2 filtered data and find average as basline
# these lists working as moving filter of size 60
S0_Base = []
S1_Base = []
S2_Base = []

# 3 lists of size BASELINE_FILTER_SIZE to store S0, S1, S2 filtered and baseline removed and thresholded data
S0_LogData = []
S1_LogData = []
S2_LogData = []

# these are the main data to determine gestures
S0_FinalData2 = []
S1_FinalData2 = []
S2_FinalData2 = []

# algorithm input parameter
PRAM_ALGO = {
    'S0_raw': 0,  # S0 raw data
    'S1_raw': 0,  # S1 raw data
    'S2_raw': 0,  # S2 raw data
    'GestureDetected': False,
    'SlopeTriggered': False,
    'DetectionTimeOut': 40,
    'Timer': 0,
    'BaselineStop': False,
    'S0_BaseAvg': 0,
    'S1_BaseAvg': 0,
    'S2_BaseAvg': 0,
    'SamplingStop': False
}

###########################################################################

def average(input_list):
    total = 0

    for i in input_list:
        total += i

    # return fixed point number
    return round(total / len(input_list))


def Algo_calc(param_in):
    # check if moving average filter is full, size = 6
    if len(S0_RawFilt) < RAW_FILTER_SIZE:

        # add raw data to their moving average filter
        S0_RawFilt.append(param_in['S0_raw'])
        S1_RawFilt.append(param_in['S1_raw'])
        S2_RawFilt.append(param_in['S2_raw'])

    # print("waiting for more raw data...")
    else:

        # throw away the first value in the S0_RawFilt list, to ensure size of the list = RAW_FILTER_SIZE
        S0_RawFilt.pop(0)
        S1_RawFilt.pop(0)
        S2_RawFilt.pop(0)

        # add new value into the S0_RawFilt list and make sure size = RAW_FILTER_SIZE
        S0_RawFilt.append(param_in['S0_raw'])
        S1_RawFilt.append(param_in['S1_raw'])
        S2_RawFilt.append(param_in['S2_raw'])

        # find S0-2 filtered raw
        S0_Filtered = average(S0_RawFilt)
        S1_Filtered = average(S1_RawFilt)
        S2_Filtered = average(S2_RawFilt)

        # debug, for porting use
        # OutputFile.write(str(S0_Filtered) + " " +str(S1_Filtered) + " " + str(S2_Filtered) + "\n")

        # check if baseline filter list is full, size 60 (1.5 seconds)
        if len(S0_Base) == BASELINE_FILTER_SIZE:
            # throw away the first value in the S0_Base list, to ensure size of the list = BASELINE_FILTER_SIZE
            S0_Base.pop(0)
            S1_Base.pop(0)
            S2_Base.pop(0)

        # if baseline update is on-going (no gesture), add S0-2 filtered raw to baseline average list
        if param_in['BaselineStop'] == False:
            # add S0_Filtered - S2_Filtered to their baseline filter list
            S0_Base.append(S0_Filtered)
            S1_Base.append(S1_Filtered)
            S2_Base.append(S2_Filtered)

            # S0_Base.append(S0_Filtered)

            # find baseline, start algorithm
            ###############################
            ###############################
            param_in['S0_BaseAvg'] = average(S0_Base)
            param_in['S1_BaseAvg'] = average(S1_Base)
            param_in['S2_BaseAvg'] = average(S2_Base)

            # debug, for porting use
            OutputFile.write(str(param_in['S0_BaseAvg']) + " " + str(param_in['S1_BaseAvg']) + " " + str(
                param_in['S2_BaseAvg']) + "\n")

        # find S0-2 delta (filtered data - baseline average)
        S0_cdc = S0_Filtered - param_in['S0_BaseAvg']
        S1_cdc = S1_Filtered - param_in['S1_BaseAvg']
        S2_cdc = S2_Filtered - param_in['S2_BaseAvg']

        # debug, for porting use
        # OutputFile.write(str(S0_cdc) + " " +str(S1_cdc) + " " + str(S2_cdc) + " " + "\n")

        # check if Final Data list if full, size 60 (1.5 seconds)
        if len(S0_LogData) > BASELINE_FILTER_SIZE:
            # throw away the first value in the FinalData list, to ensure size of the list = BASELINE_FILTER_SIZE
            S0_LogData.pop(0)
            S1_LogData.pop(0)
            S2_LogData.pop(0)

        # thresholding to make decision on the sensitivity here!
        # repeat for 3 stages

        write0 = 0
        write1 = 0
        write2 = 0

        # print(len(S0_FinalData))

        if THRESHOLD_NEG < S0_cdc < THRESHOLD_POS:
            S0_LogData.append(write0)
        else:
            write0 = S0_cdc
            S0_LogData.append(write0)

        if THRESHOLD_NEG < S1_cdc < THRESHOLD_POS:
            S1_LogData.append(write1)
        else:
            write1 = S1_cdc
            S1_LogData.append(write1)

        if THRESHOLD_NEG < S2_cdc < THRESHOLD_POS:
            S2_LogData.append(write2)
        else:
            write2 = S2_cdc
            S2_LogData.append(write2)

        # for debug use
        # OutputFile.write(str(write0) + " " +str(write1) + " " + str(write2) + " " + "\n")

        # pattern finder variable declare
        # S0_original_baseline = 0
        s0max = 0
        s0min = 0
        s0max_index = 0
        s0min_index = 0
        s0delta = 0

        s1max = 0
        s1min = 0
        s1max_index = 0
        s1min_index = 0
        s1delta = 0

        s2max = 0
        s2min = 0
        s2max_index = 0
        s2min_index = 0
        s2delta = 0

        # find S0 slope to define start point of data sampling
        s0slope = S0_LogData[-1] - S0_LogData[len(S0_LogData) - 2]

        # debug, for porting use
        # OutputFile.write(str(s0slope) +"\n")

        ######################## test algorithm ######################################
        # start sampling
        if s0slope > 100 and param_in['GestureDetected'] == False:
            # remember the original S0 baseline for long press detection
            S0_original_baseline = write0
            # then stop baseline updating
            param_in['BaselineStop'] = True
            param_in['SlopeTriggered'] = True
            # print('Im here!')

            # for debug use
            LogFile.write("potential gesture detected at line" + str(lines) + "\n")

        if param_in['SlopeTriggered'] == True:
            param_in['GestureDetected'] = True
            # data logging only, not calculation yet...
            S0_FinalData2.append(write0)
            S1_FinalData2.append(write1)
            S2_FinalData2.append(write2)

            # write in debug file
            debugFile.write(str(write0) + " " + str(write1) + " " + str(write2) + " " + "\n")
            # print(len(S0_FinalData2))

            # Stop sampling and start calculation while slope goes from max to min back to middle (approx. 0)
            if -30 < s0slope < 30:
                param_in['Timer'] += 1

            if param_in['Timer'] >= 3:

                print(len(S0_FinalData2))

                s0max = max(S0_FinalData2)
                s0min = min(S0_FinalData2)
                s0max_index = S0_FinalData2.index(s0max)
                s0min_index = S0_FinalData2.index(s0min)
                s0delta = s0max - s0min

                s1max = max(S1_FinalData2)
                s1min = min(S1_FinalData2)
                s1max_index = S1_FinalData2.index(s1max)
                s1min_index = S1_FinalData2.index(s1min)
                s1delta = s1max - s1min

                s2max = max(S2_FinalData2)
                s2min = min(S2_FinalData2)
                s2max_index = S2_FinalData2.index(s2max)
                s2min_index = S2_FinalData2.index(s2min)
                s2delta = s2max - s2min
                # check if it is UD or LR!
                # first it is UD
                if s1delta > 300 and s1delta >= s2delta:
                    if s1max_index < s1min_index:
                        # This is swipe down
                        print("Swipe DOWN")
                        LogFile.write("Swipe DOWN\n")
                        LogFile.write("s1max = " + str(s1max) + ", s1min = " + str(s1min) + '\n')
                        LogFile.write("maxindex = " + str(s1max_index) + ", minindex = " + str(s1min_index) + '\n')
                        LogFile.write("s2max = " + str(s2max) + ", s2min = " + str(s2min) + '\n')
                        LogFile.write("maxindex = " + str(s2max_index) + ", minindex = " + str(s2min_index) + '\n')
                        # debug use
                        LogFile.write("Gesture length is " + str(len(S0_FinalData2)) + "\n\n")
                    else:
                        # This is swipe up
                        print("Swipe UP")
                        LogFile.write("Swipe UP\n")
                        LogFile.write("s1max = " + str(s1max) + ", s1min = " + str(s1min) + '\n')
                        LogFile.write("maxindex = " + str(s1max_index) + ", minindex = " + str(s1min_index) + '\n')
                        LogFile.write("s2max = " + str(s2max) + ", s2min = " + str(s2min) + '\n')
                        LogFile.write("maxindex = " + str(s2max_index) + ", minindex = " + str(s2min_index) + '\n')
                        # debug use
                        LogFile.write("Gesture length is " + str(len(S0_FinalData2)) + "\n\n")
                elif s2delta > 300 and s2delta > s1delta:
                    if s2max_index < s2min_index:
                        # This is swipe left
                        print("Swipe LEFT")
                        LogFile.write("Swipe LEFT\n")
                        LogFile.write("s1max = " + str(s1max) + ", s1min = " + str(s1min) + '\n')
                        LogFile.write("maxindex = " + str(s1max_index) + ", minindex = " + str(s1min_index) + '\n')
                        LogFile.write("s2max = " + str(s2max) + ", s2min = " + str(s2min) + '\n')
                        LogFile.write("maxindex = " + str(s2max_index) + ", minindex = " + str(s2min_index) + '\n')
                        # debug use
                        LogFile.write("Gesture length is " + str(len(S0_FinalData2)) + "\n\n")
                    else:
                        print("Swipe RIGHT")
                        LogFile.write("Swipe RIGHT\n")
                        LogFile.write("s1max = " + str(s1max) + ", s1min = " + str(s1min) + '\n')
                        LogFile.write("maxindex = " + str(s1max_index) + ", minindex = " + str(s1min_index) + '\n')
                        LogFile.write("s2max = " + str(s2max) + ", s2min = " + str(s2min) + '\n')
                        LogFile.write("maxindex = " + str(s2max_index) + ", minindex = " + str(s2min_index) + '\n')
                        # debug use
                        LogFile.write("Gesture length is " + str(len(S0_FinalData2)) + "\n\n")
                elif len(S0_FinalData2) >= 5:
                    # response detected but no gesture can be recognized
                    # this might just be D-click?
                    print("///")
                    LogFile.write(" - - - \n")
                    LogFile.write("s1max = " + str(s1max) + ", s1min = " + str(s1min) + '\n')
                    LogFile.write("maxindex = " + str(s1max_index) + ", minindex = " + str(s1min_index) + '\n')
                    LogFile.write("s2max = " + str(s2max) + ", s2min = " + str(s2min) + '\n')
                    LogFile.write("maxindex = " + str(s2max_index) + ", minindex = " + str(s2min_index) + '\n')
                    # debug use
                    LogFile.write("Gesture length is " + str(len(S0_FinalData2)) + "\n\n")

                param_in['SlopeTriggered'] = False
                param_in['BaselineStop'] = False
                param_in['GestureDetected'] = False
                param_in['Timer'] = 0

                del S0_FinalData2[:]
                del S1_FinalData2[:]
                del S2_FinalData2[:]


# while loop in main...
while 1:

    dataline = InputFile.readline()

    if dataline:
        S0data = 0
        S1data = 0
        S2data = 0

        list_lines = dataline.split()

        # read raw data from raw data file
        PRAM_ALGO['S0_raw'] = int(list_lines[0])
        PRAM_ALGO['S1_raw'] = int(list_lines[1])
        PRAM_ALGO['S2_raw'] = int(list_lines[2])

        ##########################################
        ####### Input to Algorithm here ##########
        ##########################################
        Algo_calc(PRAM_ALGO)

        lines += 1
    else:
        break

# dataline = InputFile.readline()

# for debug use
# print(lines)
# print(len(S0_Base))
# print(len(S0_RawFilt))
InputFile.close()
OutputFile.close()
LogFile.close()
debugFile.close()
