import re

with open('templates/triage/create_triage.html', 'r', encoding='utf-8') as f:
    content = f.read()

# I want to find all occurrences of:
# <div style="position:relative;">
#   <textarea class="wizard-textarea" ... maxlength="(\d+)".*?></textarea>
#   <div style="text-align:right; font-size:12px; color:#555; margin-top:4px;"[^>]*>0/\1</div>
# </div>

def repl_counter(m):
    max_len = m.group(1)
    
    # We'll use a specific class for the textarea and the counter to hook JS, and position absolute
    textarea_str = m.group(0)
    
    # Extract the textarea part
    ta_match = re.search(r'<textarea.*?</textarea>', textarea_str, re.DOTALL)
    ta_html = ta_match.group(0)
    
    # Add a class to hook JS easily if it doesn't have an ID, or even if it does
    if 'counted-textarea' not in ta_html:
        ta_html = ta_html.replace('class="wizard-textarea"', 'class="wizard-textarea counted-textarea"')
    
    # Ensure it has padding-bottom so text doesn't hit the counter
    if 'style="' in ta_html:
        ta_html = ta_html.replace('style="', 'style="padding-bottom:30px; ')
    else:
        ta_html = ta_html.replace('<textarea', '<textarea style="padding-bottom:30px;"')

    return f'''<div style="position:relative;">
          {ta_html}
          <div class="char-counter" style="position:absolute; bottom:15px; right:20px; font-size:14px; color:#000;">0/{max_len}</div>
        </div>'''

# The regex needs to be carefully crafted
pattern = r'<div style="position:relative;">\s*<textarea[^>]*maxlength="(\d+)"[^>]*>.*?</textarea>\s*<div[^>]*>0/\1</div>\s*</div>'

new_content = re.sub(pattern, repl_counter, content, flags=re.DOTALL)

# Let's also update the JS to handle all `.counted-textarea` instead of just `queixa-textarea`
js_old = '''    // Contador de caracteres para queixa principal
    const queixaTA = document.getElementById('queixa-textarea');
    const queixaCounter = document.getElementById('queixa-counter');
    if (queixaTA && queixaCounter) {
      queixaTA.addEventListener('input', function() {
        queixaCounter.textContent = queixaTA.value.length + '/200';
      });
    }'''

js_new = '''    // Contador de caracteres (genérico)
    document.querySelectorAll('.counted-textarea').forEach(function(ta) {
      const counter = ta.parentElement.querySelector('.char-counter');
      if (counter) {
        ta.addEventListener('input', function() {
          const max = ta.getAttribute('maxlength');
          counter.textContent = ta.value.length + '/' + max;
        });
      }
    });'''

if js_old in new_content:
    new_content = new_content.replace(js_old, js_new)

with open('templates/triage/create_triage.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated HTML with absolute positioned counters")
