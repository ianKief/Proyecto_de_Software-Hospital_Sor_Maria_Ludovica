def validar_operando(operando):
    if(operando.isnumeric()):
        return True
    else:
        print(f"Operando {operando} inválido. Debe ingresar un número.")
        return False

def validar_divisor(div):
    if div != 0:
        return True
    else:
        print("Operando invalido. El divisor no puede ser 0")
        return False