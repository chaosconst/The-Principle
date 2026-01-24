from graphviz import Digraph
import os

dot = Digraph(comment='Character Data Flow', format='png')
dot.attr(rankdir='TB', bgcolor='#050510')
dot.attr('node', shape='box', style='filled', fillcolor='#1a1a1a', fontcolor='white', fontname='Arial')
dot.attr('edge', color='#00ffff')

# Nodes
dot.node('DB', 'MongoDB (stories)', shape='cylinder', fillcolor='#2d2d2d')
dot.node('SD', 'story_dict (Memory)', shape='folder', fillcolor='#333333')
dot.node('CDB', 'character_db\n(Full List)', style='dashed')
dot.node('FUNC', 'gen_story_text_for_api\n(The Assembler)', shape='component', fillcolor='#003366')

dot.node('FILTER', 'Filter Logic\n(Location/Active/Main)', shape='diamond', fillcolor='#663300')
dot.node('FORMAT', 'Formatter\n(Name + Desc + Status)', shape='note')
dot.node('PROMPT', 'Final Prompt Context\n(To LLM)', shape='doc', fillcolor='#004400')

# Edges
dot.edge('DB', 'SD', 'Load')
dot.edge('SD', 'CDB', 'Get')
dot.edge('CDB', 'FUNC', 'Input')
dot.edge('FUNC', 'FILTER', 'Iterate Characters')
dot.edge('FILTER', 'FORMAT', 'Selected Chars')
dot.edge('FILTER', 'FUNC', 'Discarded (Inactive)')
dot.edge('FORMAT', 'PROMPT', 'Append to Text')

# Context
dot.node('HIST', 'History/Notes', shape='note')
dot.edge('HIST', 'PROMPT', 'Combine')

output_path = os.path.expanduser('~/pob_server/uploads/character_flow')
dot.render(output_path, cleanup=True)
print(f"Generated: {output_path}.png")
