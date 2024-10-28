# Parser de Ficheiros MEPS

## Descrição

Este parser foi desenvolvido para processar ficheiros MEPS (Pagamento Serviço) de acordo com as especificações da SISP (Sociedade Interbancária e Sistemas de Pagamentos). O parser suporta ambas as versões do formato de registo tipo 2 (versão 1 e versão 2) e realiza validações automáticas dos dados.

## Requisitos

- Python 3.7 ou superior
- Não são necessárias bibliotecas externas além da biblioteca padrão Python

## Instalação

1. Copie o ficheiro `meps_parser.py` para o seu projeto
2. Importe a classe e funções necessárias:

```python
from meps_parser import MEPSFileParser
```

## Estrutura do Ficheiro MEPS

O ficheiro MEPS é composto por três tipos de registos:

- Registo Header (tipo 0): Contém informações gerais do ficheiro
- Registo Detalhe (tipo 2): Contém detalhes das transações
- Registo Trailer (tipo 9): Contém totais e sumários

### Diferenças entre Versões do Registo Tipo 2

- **Versão 1**: Campo TARIFAPS com 5 dígitos
- **Versão 2**: Campo TARIFAPS com 10 dígitos

## Como Usar

### Exemplo Básico

```python
from meps_parser import MEPSFileParser

# Processar um ficheiro MEPS
def process_meps_file(file_path: str):
    parser = MEPSFileParser()
    try:
        resultado = parser.parse_file(file_path)

        # Acessar dados do header
        header = resultado['header']
        print(f"ID do Ficheiro: {header.idfich}")
        print(f"Entidade: {header.entidade}")

        # Acessar transações
        detalhes = resultado['details']
        for detalhe in detalhes:
            print(f"Referência: {detalhe.refpag}")
            print(f"Montante: {detalhe.montpgps}")
            print(f"Tarifa: {detalhe.tarifaps}")

        # Acessar totais
        trailer = resultado['trailer']
        print(f"Total de Transações: {trailer.totreg}")
        print(f"Montante Total: {trailer.montranps}")
        print(f"Total de Tarifas: {trailer.tottarps}")

    except Exception as e:
        print(f"Erro ao processar ficheiro: {str(e)}")
        raise

if __name__ == "__main__":
    file_path = "files/MEPS_00029_20241027011323_1"
    process_meps_file(file_path)
```

### Uso Avançado

```python
from meps_parser import MEPSFileParser

# Criar uma instância do parser
parser = MEPSFileParser()

# Processar ficheiro com acesso a todos os métodos
resultado = parser.parse_file("caminho_do_ficheiro.txt")

# Acessar campos específicos
for detalhe in resultado['details']:
    # Verificar versão do registo
    if detalhe.version == 1:
        print("Registo Versão 1")
    else:
        print("Registo Versão 2")

    # Acessar informações do terminal
    print(f"Tipo de Terminal: {detalhe.tipoterm}")
    print(f"ID do Terminal: {detalhe.idterminal}")
    print(f"Localização: {detalhe.locmorter}")
```

## Campos Disponíveis

### Header (MEPSHeader)

- `tipreg`: Tipo de registo (0)
- `fich`: Tipo de ficheiro ("MEPS")
- `idinstori`: ID da instituição de origem
- `idinstdes`: ID da instituição de destino
- `idfich`: ID do ficheiro
- `idfichant`: ID do ficheiro anterior
- `entidade`: Entidade
- `codmoeda`: Código da moeda
- `taxaiva`: Taxa de IVA
- `idfichedst`: ID do ficheiro EDST

### Detalhe (MEPSDetail)

- `tipreg`: Tipo de registo (2)
- `codproc`: Código de processamento
- `idlog`: ID do log
- `nrlog`: Número do log central
- `dthora`: Data/hora
- `montpgps`: Montante do pagamento
- `tarifaps`: Tarifa
- `tipoterm`: Tipo de terminal
- `idterminal`: ID do terminal
- `identranps`: ID da transação local
- `locmorter`: Localização do terminal
- `refpag`: Referência do pagamento
- `modenv`: Modo de envio
- `codresp`: Código de resposta
- `nridresps`: ID da mensagem da empresa
- `version`: Versão do registo (1 ou 2)

### Trailer (MEPSTrailer)

- `tipreg`: Tipo de registo (9)
- `totreg`: Número total de registos
- `montranps`: Montante total das transações
- `tottarps`: Total das tarifas
- `valiva`: Valor do IVA

## Validações Automáticas

O parser realiza as seguintes validações:

1. Presença de todos os registos obrigatórios
2. Contagem correta de registos
3. Consistência dos totais monetários
4. Cálculos de tarifas e montantes

## Tratamento de Erros

O parser lança exceções específicas em caso de:

- Ficheiro mal formatado
- Registos em falta
- Inconsistências nos totais
- Erros de validação

## Notas Importantes

1. Todos os valores monetários são convertidos para Decimal com 2 casas decimais
2. Os campos são automaticamente limpos de espaços em branco
3. A versão do registo tipo 2 é detectada automaticamente
4. As validações são realizadas após a leitura completa do ficheiro

## Suporte

Em caso de dúvidas ou problemas, contacte:

- Email: DSI-DEV-RPA@cvt.cv
