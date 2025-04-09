# Gerador de SQL para GLPI 10

Uma aplicação web para gerar scripts SQL para o GLPI 10 a partir de planilhas Excel. Esta ferramenta ajuda administradores e desenvolvedores a criar facilmente instruções SQL de inserção para tabelas de banco de dados do GLPI 10 com base em dados estruturados do Excel.

## Funcionalidades

- **Autenticação de Usuário**: Sistema de login seguro com variáveis de ambiente
- **Upload de Excel**: Envio de arquivos Excel com validação para as abas necessárias
- **Geração de SQL**: Geração automática de instruções SQL a partir de dados do Excel
- **Pré-visualização**: Visualize o SQL gerado antes de baixar
- **Seleção de Módulos**: Escolha quais módulos incluir na saída SQL
- **Exportação**: Baixe o script SQL gerado
- **Suporte a Docker**: Implantação fácil com Docker e Docker Compose

## Capturas de Tela

![Tela de Login](https://via.placeholder.com/800x450.png?text=Tela+de+Login)
![Dashboard](https://via.placeholder.com/800x450.png?text=Dashboard)
![Página de Upload](https://via.placeholder.com/800x450.png?text=Página+de+Upload)
![Pré-visualização SQL](https://via.placeholder.com/800x450.png?text=Pré-visualização+SQL)

## Instalação

### Pré-requisitos

- Docker e Docker Compose
- Git

### Opção 1: Usando Docker (Recomendado)

1. Clone o repositório:
   ```bash
   git clone https://github.com/seuusuario/gerador_sql_glpi10.git
   cd gerador_sql_glpi10