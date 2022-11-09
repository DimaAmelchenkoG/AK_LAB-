#!/usr/bin/python3
# pylint: disable=missing-function-docstring  # что бы не быть капитаном очевидностью
# pylint: disable=invalid-name                # сохраним традиционные наименования сигналов
# pylint: disable=consider-using-f-string     # избыточный синтаксис

"""Транслятор brainfuck в машинный код
"""

import sys

from isa import Opcode, write_code, Term

# словарь символов, непосредственно транслирумых в машинный код
symbol2opcode = {
    "<": Opcode.LEFT,
    ">": Opcode.RIGHT,
    "+": Opcode.INC,
    "-": Opcode.DEC,
    ",": Opcode.INPUT,
    ".": Opcode.PRINT,
}

# полное множество символов языка brainfuck
symbols = {"<", ">", "+", "-", ",", ".", "[", "]"}


def translate(text):
    # Транслируем текст в последовательность значимых термов.
    terms = []
    for line_num, line in enumerate(text.split(), 1):
        for pos, char in enumerate(line, 1):
            if char in symbols:
                # любые другие символы рассматриваются как комментарии, по этому выкидываем
                terms.append(Term(line_num, pos, char))

    # Проверяем корректность программы: скобки должны быть парными.
    deep = 0
    for term in terms:
        if term.symbol == "[":
            deep += 1
        if term.symbol == "]":
            deep -= 1
        assert deep >= 0, "Unbalanced parentness!"
    assert deep == 0, "Unbalanced parentness!"

    # Транслируем термы в машинный код.
    code = []
    jmp_stack = []
    for pc, term in enumerate(terms):
        if term.symbol == '[':
            # оставляем placeholder, который будет заменён в конце цикла
            code.append(None)
            jmp_stack.append(pc)
        elif term.symbol == ']':
            # формируем цикл с началом из jmp_stack
            begin_pc = jmp_stack.pop()
            begin = {'opcode': Opcode.JZ, 'arg': pc + 1, 'term': terms[begin_pc]}
            end = {'opcode': Opcode.JMP,
                   'arg': begin_pc, 'term': term}
            code[begin_pc] = begin
            code.append(end)
        else:
            # Обработка тривиально отображаемых операций.
            code.append({'opcode': symbol2opcode[term.symbol], 'term': term})

    # Добавляем инструкцию остановки процессора в конец программы.
    code.append({'opcode': Opcode.HALT})
    return code


def main(args):
    """Функция запуска транслятора.

    Реализована таким образом так как:

    - ограничить область видимости внутренних переменных;
    - упростить автоматическое тестирование.
    """
    assert len(args) == 2, \
        "Wrong arguments: translator.py <input_file> <target_file>"
    source, target = args

    with open(source, "rt", encoding="utf-8") as f:
        source = f.read()

    code = translate(source)
    write_code(target, code)


if __name__ == '__main__':
    main(sys.argv[1:])
