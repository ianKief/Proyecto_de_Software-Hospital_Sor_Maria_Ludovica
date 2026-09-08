def validar_operando(operando):
    if(operando.isnumeric()):
        return True
    else:
        print(f"Operando {operando} inválido. Debe ingresar un número.")
        return False