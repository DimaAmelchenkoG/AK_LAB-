import json
import logging
import sys

from isa import Opcode


class DataPath:
    data_memory_size = None
    data_memory = None
    address_register = None
    acc = None
    instruction_pointer = None
    buffer_register = None
    data_register = None
    muxDCP_value = None
    muxAB_value = None
    alu_right = None
    alu_left = None
    alu = None
    mux_main_value = None
    zero = None
    input_buffer = None
    output_buffer = None
    tick_counter = None

    def __init__(self, data_memory_size, input_buffer1):
        assert data_memory_size > 0, "Data_memory size should be non-zero"
        self.data_memory_size = data_memory_size
        self.data_memory = [0] * data_memory_size
        self.address_register = 0
        self.buffer_register = 0
        self.acc = 0
        self.instruction_pointer = 0
        self.data_register = 0
        self.muxDCP_value = 0
        self.muxAB_value = 0
        self.alu_right = 0
        self.alu_left = 0
        self.alu = 0
        self.mux_main_value = 0
        self.zero = True
        self.tick_counter = 0
        self.input_buffer = input_buffer1
        self.output_buffer = []

    def init_memory(self, code):
        data_start_addres = 4
        vars = []
        default_text = []
        input_text = []


        for line in code:
            opcode = line["opcode"]
            if opcode == Opcode.VAR:
                arg = line["arg"]
                if str(arg).isdigit():
                    vars.append({"name": line["name"], "value": arg, "old_address": line["index"]})
                elif len(arg) > 2:
                    default_text.append({"name": line["name"], "value": arg, "old_address": line["index"]})
                else:
                    input_text.append({"name": line["name"], "old_address": line["index"]})

        count_of_vars = 0
        for var in vars:
            self.data_memory[data_start_addres + count_of_vars] = var["value"]
            var["new_address"] = data_start_addres + count_of_vars
            count_of_vars += 1

        address_after_vars = data_start_addres + count_of_vars
        count_of_symbols = 0
        count_of_texts = 0
        for texts in default_text:
            text = texts["value"][1:-1]
            self.data_memory[
                address_after_vars + count_of_symbols + count_of_texts] = address_after_vars + count_of_texts + count_of_symbols + 1
            for dt in default_text:
                if dt["value"][1:-1] == text:
                    dt["new_address"] = address_after_vars + count_of_symbols + count_of_texts
            for symbols in text:
                self.data_memory[address_after_vars + count_of_symbols + count_of_texts + 1] = symbols
                count_of_symbols += 1
            self.data_memory[address_after_vars + count_of_symbols + (count_of_texts + 1) * 2] = 0
            count_of_symbols += 1
            count_of_texts += 1

        start_of_instr = data_start_addres + count_of_vars + count_of_symbols + count_of_texts

        count_of_instr_for_reserved = 0
        for line in code:
            opcode = line["opcode"]
            if opcode != Opcode.VAR:
                count_of_instr_for_reserved += 1

        reserved = count_of_instr_for_reserved + start_of_instr + 1

        if len(input_text) > 0:
            input_text[0]["new_address"] = reserved
            self.data_memory[reserved] = reserved + 1



        count_of_inputs = 0
        for line in code:
            if "arg" in line and line["arg"] == "\"\"":
                count_of_inputs += 1


        count_of_instr = 0
        for line in code:
            opcode = line["opcode"]
            if opcode != Opcode.VAR:
                address = start_of_instr + count_of_instr
                arg = "-"
                if "arg" in line:
                    if opcode == Opcode.JMP or opcode == Opcode.JNZ or opcode == Opcode.JZ:
                        arg = line["arg"] + data_start_addres + count_of_symbols - count_of_inputs
                    else:
                        if str(line["arg"]).isdigit():
                            if "kosven" in line:
                                for dt in default_text:
                                    if dt["old_address"] == line["arg"]:
                                        arg = dt["new_address"]
                                for dt in vars:
                                    if dt["old_address"] == line["arg"]:
                                        arg = dt["new_address"]
                                for dt in input_text:
                                    if dt["old_address"] == line["arg"]:
                                        arg = dt["new_address"]
                                arg = '&' + str(arg)
                            else:
                                for dt in default_text:
                                    if dt["old_address"] == line["arg"]:
                                        arg = dt["new_address"]
                                for dt in vars:
                                    if dt["old_address"] == line["arg"]:
                                        arg = dt["new_address"]
                                for dt in input_text:
                                    if dt["old_address"] == line["arg"]:
                                        arg = dt["new_address"]
                                # arg = line["arg"] + data_start_addres
                        else:
                            arg = line["arg"]

                instr = {"opcode": Opcode(opcode), "arg": arg}
                self.data_memory[address] = instr
                count_of_instr += 1


        self.data_memory[0] = start_of_instr
        self.instruction_pointer = self.data_memory[0]

    def tick(self):
        self.tick_counter += 1

    def latch_acc(self):
        self.acc = self.alu

    def get_alu_result(self, opcode):
        if opcode == Opcode.LOAD:
            self.alu = self.alu_right
        if opcode == Opcode.ADD:
            self.alu = (self.alu_right + self.alu_left) % 4294967296
        if opcode == Opcode.SUB:
            self.alu = (self.alu_left - self.alu_right) % 4294967296
        if opcode == Opcode.MUL:
            self.alu = (self.alu_left * self.alu_right) % 4294967296
        if opcode == Opcode.DIV:
            self.alu = (self.alu_left // self.alu_right) % 4294967296
        if opcode == Opcode.INC:
            self.alu = (self.alu_right + 1) % 4294967296

        if opcode == Opcode.MOD:
            self.alu = self.alu_left % self.alu_right

        if self.alu == 0:
            self.zero = True
        else:
            self.zero = False

    def getMuxDCP(self, sel, arg):
        if sel == "MEM":
            self.muxDCP_value = self.data_memory[arg]
        if sel == "DR":
            self.muxDCP_value = self.data_register
        if sel == "IP":
            self.muxDCP_value = self.instruction_pointer

    def getMuxAB(self, sel):
        if sel == "ACC":
            self.muxAB_value = self.acc
        if sel == "BR":
            self.muxAB_value = self.buffer_register

    def latch_alu_right(self):
        self.alu_right = self.muxDCP_value

    def latch_alu_left(self):
        self.alu_left = self.muxAB_value




    def latch_address_register(self, address):
        if str(address).isdigit():
            self.address_register = address
        elif address[0] == '$':
            self.address_register = address
        elif address[0] == '&':
            self.address_register = int(self.data_memory[int(address[1:])])

    def latch_data_register(self, read_write):
        if read_write == 'r':
            if str(self.address_register)[0] == '$':
                self.data_register = int(self.address_register[1:])
            else:
                self.data_register = self.data_memory[self.address_register]

        if read_write == 'w':
            self.data_register = self.acc


    def latch_memory(self, address):
        self.data_memory[self.address_register] = self.data_register

    def signal_read(self):
        symbol = self.acc
        self.output_buffer.append(symbol)

    def signal_write(self, arg):
        symbol = self.input_buffer.pop(0)
        self.acc = symbol
        #if arg.startswith('&'):
            #symbol = self.input_buffer.pop(0)
            #self.data_memory[self.data_memory[int(arg[1:])]] = symbol
            #self.acc = symbol

    def setZero(self):
        if self.acc == 0:
            self.zero = True
        else:
            self.zero = False



class ControlUnit:
    program = None
    program_counter = None
    data_path = None
    tick = None
    count_of_instr = None

    def __init__(self, program, data_path):
        self.program = program
        self.program_counter = 0
        self.data_path = data_path
        self.tick = 0
        self.count_of_instr = 0

    def printState(self):
        print("Tick:", self.data_path.tick_counter,
              "ACC:", self.data_path.acc,
              "ALU:", self.data_path.alu,
              "DR:", self.data_path.data_register,
              "ZERO:", self.data_path.zero)

    def address_decoder(self, arg):
        if arg == 'in':
            arg = 1
        elif arg == 'out':
            arg = 2

        if arg == 2:
            self.data_path.signal_read()
            self.data_path.tick()
            return True
        elif arg == 1:
            self.data_path.signal_write(arg)
            self.data_path.setZero()
            self.data_path.tick()
            return True
        else:
            return False

    def __repr__(self):
        state_repr = "TICK: {:1}   PC: {:1}   ACC: {:1}  DR: {}  ZERO: {}".format(
            self.data_path.tick_counter,
            self.count_of_instr,
            self.data_path.acc,
            self.data_path.data_register,
            self.data_path.zero
        )

        if self.data_path.instruction_pointer != self.data_path.data_memory[0]:
            instr = self.data_path.data_memory[self.data_path.instruction_pointer - 1]

            opcode = instr["opcode"]
            instr_repr = str(opcode)

            if "arg" in instr:
                instr_repr += "{}".format(instr["arg"])

            ret = "{} \t{}".format(state_repr, instr_repr)
        else:
            ret = state_repr


        return ret

    def decode_and_execute_instruction(self):
        self.count_of_instr += 1
        instr = self.data_path.data_memory[self.data_path.instruction_pointer]
        arg = instr["arg"]
        opcode = instr["opcode"]
        #print(opcode, arg)


        if opcode == Opcode.LOAD:
            if not(self.address_decoder(arg)):
                self.data_path.latch_address_register(arg)
                self.data_path.tick()

                self.data_path.latch_data_register('r')
                self.data_path.tick()

                self.data_path.getMuxDCP("DR", arg)
                self.data_path.latch_alu_right()
                self.data_path.tick()

                self.data_path.get_alu_result(opcode)
                self.data_path.latch_acc()
                self.data_path.tick()

        if opcode == Opcode.ST:
            if not(self.address_decoder(arg)):
                self.data_path.latch_data_register('w')
                self.data_path.tick()

                self.data_path.latch_address_register(arg)
                self.data_path.latch_memory(arg)
                self.data_path.tick()

        if opcode == Opcode.JNZ:
            if self.data_path.zero == False:
                self.data_path.instruction_pointer = arg - 1
            self.data_path.tick()

        if opcode == Opcode.JZ:
            if self.data_path.zero == True:
                self.data_path.instruction_pointer = arg - 1
            self.data_path.tick()

        if opcode == Opcode.JMP:
            self.data_path.instruction_pointer = arg - 1
            self.data_path.tick()

        if opcode == Opcode.ADD:
            #
            self.data_path.latch_address_register(arg)
            self.data_path.tick()
            self.data_path.latch_data_register('r')
            self.data_path.tick()

            self.data_path.getMuxDCP("DR", arg)
            self.data_path.latch_alu_right()

            self.data_path.tick()
            self.data_path.getMuxAB("ACC")
            self.data_path.latch_alu_left()
            self.data_path.tick()

            self.data_path.get_alu_result(opcode)
            self.data_path.tick()

            self.data_path.latch_acc()
            self.data_path.tick()

        if opcode == Opcode.MOD:

            self.data_path.latch_address_register(arg)
            self.data_path.tick()

            self.data_path.latch_data_register( 'r')
            self.data_path.tick()

            self.data_path.getMuxDCP("DR", arg)
            self.data_path.latch_alu_right()
            self.data_path.tick()

            self.data_path.getMuxAB("ACC")
            self.data_path.latch_alu_left()
            self.data_path.tick()

            self.data_path.get_alu_result(opcode)
            self.data_path.latch_acc()
            self.data_path.tick()

            self.data_path.setZero()
            self.data_path.tick()


        if opcode == Opcode.SUB:

            self.data_path.latch_address_register(arg)
            self.data_path.tick()

            self.data_path.latch_data_register('r')
            self.data_path.tick()


            self.data_path.getMuxDCP("DR", arg)
            self.data_path.latch_alu_right()
            self.data_path.tick()

            self.data_path.getMuxAB("ACC")
            self.data_path.latch_alu_left()
            self.data_path.tick()

            self.data_path.get_alu_result(opcode)
            self.data_path.latch_acc()
            self.data_path.tick()

            self.data_path.setZero()
            self.data_path.tick()

        if opcode == Opcode.MUL:

            self.data_path.latch_address_register(arg)
            self.data_path.tick()

            self.data_path.latch_data_register('r')
            self.data_path.tick()


            self.data_path.getMuxDCP("DR", arg)
            self.data_path.latch_alu_right()
            self.data_path.tick()

            self.data_path.getMuxAB("ACC")
            self.data_path.latch_alu_left()
            self.data_path.tick()

            self.data_path.get_alu_result(opcode)
            self.data_path.latch_acc()
            self.data_path.tick()

            self.data_path.setZero()
            self.data_path.tick()

        if opcode == Opcode.DIV:

            self.data_path.latch_address_register(arg)
            self.data_path.tick()

            self.data_path.latch_data_register('r')
            self.data_path.tick()


            self.data_path.getMuxDCP("DR", arg)
            self.data_path.latch_alu_right()
            self.data_path.tick()

            self.data_path.getMuxAB("ACC")
            self.data_path.latch_alu_left()
            self.data_path.tick()

            self.data_path.get_alu_result(opcode)
            self.data_path.latch_acc()
            self.data_path.tick()

            self.data_path.setZero()
            self.data_path.tick()

        if opcode == Opcode.INC:

            self.data_path.latch_address_register(arg)
            self.data_path.tick()

            self.data_path.latch_data_register('r')
            self.data_path.tick()

            self.data_path.getMuxDCP("DR", arg)
            self.data_path.latch_alu_right()
            self.data_path.tick()

            self.data_path.get_alu_result(opcode)
            self.data_path.latch_acc()
            self.data_path.tick()

            self.data_path.latch_data_register('w')
            self.data_path.tick()

            self.data_path.latch_memory(arg)
            self.data_path.tick()

            self.data_path.setZero()
            self.data_path.tick()



        if opcode == Opcode.PRINT:
            # print("PRINT", arg, self.data_path.acc)
            self.data_path.signal_read()
            self.data_path.tick()

        if opcode == Opcode.READ:
            # print('READ', arg)
            self.data_path.signal_write(arg)
            self.data_path.setZero()
            self.data_path.tick()

        if opcode == Opcode.HALT:
            self.data_path.tick()
            raise StopIteration()

        self.data_path.instruction_pointer += 1

        #self.printState()
        #for i in range(70):
            #print(i, self.data_path.data_memory[i])

        # instr = self.program[self.program_counter]
        # opcode = instr["opcode"]
        # print(opcode)


def simulation(code, data_memory_size, limit, input_buffer):
    data_path = DataPath(data_memory_size, input_buffer)
    control_unit = ControlUnit(code, data_path)
    instr_counter = 0

    data_path.init_memory(code)
    #for i in range(25):
        #print(i, data_path.data_memory[i])
    #print("----------")
    i = 0

    #logging.debug(control_unit)
    try:
        while True:
            control_unit.decode_and_execute_instruction()
            #logging.debug(control_unit)
            instr_counter += 1
            if i == 100000:
                break
            i += 1
    except StopIteration:
        data_path.instruction_pointer += 1
        instr_counter += 1
        logging.debug(control_unit)


    if instr_counter > limit:
        logging.warning("Exceed limit!")

        #logging.debug(control_unit)
        #print("STOP")
        a = 0
    #for i in range(25):
        #print(i, data_path.data_memory[i])
    return data_path.output_buffer, instr_counter, data_path.tick_counter



def main(code_file, input_file):
    code = []

    # если адрес > 1000
    # если адрес равен 3-м, то отправояем в устройство вывода

    with open(code_file) as f:
        code = json.load(f)

    input_buffer = []
    with open(input_file) as f:
        for sym in f.read():
            input_buffer.append(sym)

    #input_buffer = []

    if len(input_buffer) > 0:
        input_buffer.append(0)





    #for a in code:
        #print(a)
    #print("---------")

    output, instr_counter, ticks = simulation(
        code,
        data_memory_size=1000,
        limit=100000,
        input_buffer=input_buffer
    )

    if len(output) > 0:
        print("".join(output))

    print("instr_counter: ", instr_counter, "ticks:", ticks)




if __name__ == "__main__":
    #logging.getLogger().setLevel(logging.DEBUG)
    #code_file = 'target_file.json'
    #input_file = 'input_machine.txt'
    #main(code_file, input_file)

    _, code_file, input_file = sys.argv
    main(code_file, input_file)
