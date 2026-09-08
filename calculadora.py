from validaciones import validar_operando, validar_divisor
from suma import suma
from multiplicacion import multiplicacion
from division import division

print("Iniciando calculadora...")
print("Seleccione una operación:")
print("- Suma (+)")
print("- Resta (-)")
print("- Multiplicación (*)")
print("- División (/)")

operador = input("Ingrese el operador: ")
if operador not in ['+', '-', '*', '/']:
    print("Operador no válido.")
    exit(1)

op1 = input("Ingrese el primer operando: ")
op2 = input("Ingrese el segundo operando: ")

if not validar_operando(op1) or not validar_operando(op2):
    exit(2)

op1 = int(op1)
op2 = int(op2)

match operador:
    case '+':
        resultado = suma(op1, op2)
    case '-':
        resultado = op1 - op2 # MODIFICAR
    case '*':
        resultado = multiplicacion(op1, op2) # MODIFICAR
    case '/':
        if not validar_divisor(op2): 
            exit(3)
        else:
            resultado = division(op1,op2)

print(f"El resultado de la operación es {resultado}")