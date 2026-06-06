# TODO

- [ ] Pensar em nomes finais antes da v1
     Agora é a hora de ajustar entity keys. Depois da v1.0.0, mudar primary_window_available_percent ou last_received_at vai quebrar dashboards/automações]
- [ ] Verificar a template: https://github.com/nikolajflojgaard/homeassistant-hacs-template
- [ ] run ruff check custom_components/ai_usage em pipeline
---
Quero que analise o documento docs/payload-contract.md nele tem os contratos de payload que a integração do HA (Home assistante) deve aceitar.
Agora voce deve definir e criar um outro documento que descreve os sensores e devices que a integração deve criar com base nesses payloads. 
O documento deve ser estruturado, claro e conter exemplos de cada sensor e device criado.
Use o formato markdown para criar o documento. O nome do documento deve ser `device-and-sensor-contract.md`.
Considere os padrões exigidos pelo HA para criação de devices e sensores, e como os dados do payload devem ser mapeados para esses dispositivos.

Algumas coisas a serem consideradas:
- Cada provider pode ter mais de um device.
- Os devices PROVAVELMENTE devem ser do tipo service e ter um nome que identifique o provider e a conta (regras de nomenclatura podem ser definidas depois).
  - devices devem ser criados dinamicamente quando receber a request do webhook, ou seja, não tem um número fixo de devices para cada provider.
- Cada device deve ter sensores associados que representem os dados disponíveis do provider.
- Se possivel uma entidade que mostre a imagem do provider e os dados da conta (Email, id, etc, plano).
- Os sensores devem ser atualizados a cada nova request recebida do webhook, refletindo o último estado do uso da IA para aquele provider e conta.
- Talvez um device geral que tenha informações do source e source version da integração, para controle e debug.
  - Pensar se aqui ficaria o sensor de `erro`
- Definir quais sensores são comuns entre os providers e quais são específicos de cada provider, para manter uma estrutura organizada e fácil de entender.
- Definir o formato dos estados dos sensores, para garantir consistência e facilitar o uso em automações e dashboards do HA.
- Definir o formato dos atributos dos sensores, para incluir informações adicionais relevantes que possam ser úteis para automações e dashboards do HA.

Quais quer dúvidas ou pontos que precisar de mais detalhes, me pergunte para que eu possa te ajudar a criar um documento completo e claro.
Sugestões são bem vindas

---
Pontos Para Confirmar Antes Da Implementacao
1 - Sobre a versão do HA para suporte pode pegar a mais atual que é 2026.5
2 - aceita
3 - aceito
4 - não
5 - não

Ponto de atenção, não deixe o código acoplado pois no futuro o paylod pode vim da proria integração e não do webhook, 
então pense em uma estrutura que seja fácil de adaptar para isso. Talvez um serviço que receba o payload e faça o processamento, 
e o webhook apenas chame esse serviço. Assim, no futuro, a integração pode chamar esse serviço diretamente sem precisar passar pelo webhook.