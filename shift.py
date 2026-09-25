import re

with open('templates/triage/create_triage.html', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to shift step-2 to step-24 by +1.
def repl_step(m):
    step_num = int(m.group(1))
    if step_num >= 2:
        return f'id="step-{step_num+1}"'
    return m.group(0)
    
content = re.sub(r'id="step-(\d+)"', repl_step, content)

def repl_meta(m):
    text = m.group(1)
    step_num = int(m.group(2))
    if step_num >= 2:
        step_num += 1
    return f'{text}pergunta {step_num} de 25'

content = re.sub(r'(Identificação &middot; |Vínculo institucional &middot; |Contexto clínico &middot; |Rede de apoio &middot; |Encerramento &middot; )pergunta (\d+) de 24', repl_meta, content)

# Update JS
content = content.replace('totalSteps = 24;', 'totalSteps = 25;')
content = content.replace('start: 1,  end: 4', 'start: 1,  end: 5')
content = content.replace('start: 5,  end: 7', 'start: 6,  end: 8')
content = content.replace('start: 8,  end: 11', 'start: 9,  end: 12')
content = content.replace('start: 12, end: 17', 'start: 13, end: 18')
content = content.replace('start: 18, end: 24', 'start: 19, end: 25')

with open('templates/triage/create_triage.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
