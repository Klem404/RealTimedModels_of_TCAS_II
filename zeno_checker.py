import xml.etree.ElementTree as ET
import re
import sys

#Le parsing de fichier xml n'a pas été conçu par moi , c'est l'IA qui l'a fait (ce n'est pas la partie intéressante du projet)
def parse_uppaal(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    templates = {}
    
    for template in root.findall('.//template'):
        name_node = template.find('name')
        name = name_node.text if name_node is not None else "Unknown"
        
        locations = {}
        for loc in template.findall('location'):
            loc_id = loc.get('id')
            loc_name_node = loc.find('name')
            loc_name = loc_name_node.text if loc_name_node is not None else loc_id
            
            invariant = ""
            for label in loc.findall('label'):
                if label.get('kind') == 'invariant' and label.text:
                    invariant = label.text
                    
            locations[loc_id] = {'name': loc_name, 'invariant': invariant}
            
        transitions = []
        for trans in template.findall('transition'):
            src_node = trans.find('source')
            tgt_node = trans.find('target')
            if src_node is None or tgt_node is None:
                continue
                
            src = src_node.get('ref')
            tgt = tgt_node.get('ref')
            
            guard, sync, assignment = "", "", ""
            
            for label in trans.findall('label'):
                kind = label.get('kind')
                if kind == 'guard' and label.text: guard = label.text
                elif kind == 'synchronisation' and label.text: sync = label.text
                elif kind == 'assignment' and label.text: assignment = label.text
                
            transitions.append({
                'src': src, 'tgt': tgt, 
                'guard': guard, 'sync': sync, 'assignment': assignment
            })
            
        templates[name] = {
            'locations': locations,
            'transitions': transitions
        }
        
    return templates

# Après parsing, une transition est de la forme transi = {'src': 'id_source', 'tgt': 'id_target', 'guard': 'x>5', 'sync': 'chan!', 'assignment': 'x=0'}
#Fonction pour récupérer les cycles, on utilise un parcours en profondeur.
def get_cycles(transitions):

    adj = {}
    for i, t in enumerate(transitions):
        if t['src'] not in adj: # t[src] est l'état de départ, t[tgt] est l'état d'arrivée ("target"), ici on crée la liste d'adjacence.
            adj[t['src']] = []
        adj[t['src']].append((t['tgt'], i))
    
    cycles = []
    visited_cycles = set()
    path_nodes = []
    path_edges = []
    
    def dfs(node):
        if node in path_nodes: #cv dire qu'on a trouvé un cycle !

            idx = path_nodes.index(node)
            cycle_edges_idx = path_edges[idx:] #fait pour avoir seulement le cycle, en enlevant le chemin "avant" le cycle.
            
            # On empeche les doublons ici
            cycle_tuple = tuple(sorted(cycle_edges_idx))
            if cycle_tuple not in visited_cycles:
                visited_cycles.add(cycle_tuple)
                cycles.append([transitions[i] for i in cycle_edges_idx])
            return
        
        path_nodes.append(node)
        for nxt, t_idx in adj.get(node, []):
            path_edges.append(t_idx)
            dfs(nxt)
            path_edges.pop()
        path_nodes.pop()

    for node in list(adj.keys()):
        dfs(node)
        
    return cycles

def is_strongly_non_zeno(cycle):
    resets = set()
    guards = set()
    
    for t in cycle:
        #On check les resets d'horloge dans les assignments
        if t['assignment']:
            matches = re.findall(r'\b([a-zA-Z_]\w*)\s*=\s*0\b', t['assignment'])
            for m in matches:
                resets.add(m)
                
        #On check les guards d'horloge dans les guards
        if t['guard']:
            matches = re.findall(r'\b([a-zA-Z_]\w*)\s*(?:>|>=|==)\s*([1-9]\d*)\b', t['guard'])
            for m in matches:
                guards.add(m[0])
                
    # On vérifie notre condition suffisante, si au moins une horloge est réinitialisée et a une garde stricte, alors le cycle est non-zeno.
    return len(resets.intersection(guards)) > 0

def analyze(xml_file):
    print(f"--- Zeno Analysis for {xml_file} ---\n")
    try:
        templates = parse_uppaal(xml_file)
    except Exception as e:
        print(f"Error parsing {xml_file}: {e}")
        return
        
    all_cycles = []
    
    # Ici on collecte tout les cycles de tout les templates , and on y évalue la fonction précédente pour savoir quels cycles sont "déjà" non-zeno (càd qui vérifient la condition suffisante).
    # Il y a donc ici les étapes 1 et 2 de ce qui est décrit dans les consignes.
    for t_name, data in templates.items():
        trans = data['transitions']
        locations = data['locations']
        cycles = get_cycles(trans)
        
        for c in cycles:
            all_cycles.append({
                'template': t_name,
                'locations_dict': locations, 
                'transitions': c,
                'is_snz': is_strongly_non_zeno(c),
                'syncs': [t['sync'] for t in c if t['sync']]
            })
            
    # Etape 3 : On regroupe les cycles selon les synchronisations, pour pouvoir ensuite vérifier si un ensemble de cycles synchronisés est potentiellement dangereux.
    independent_loops = [] #les cycles qui n'ont pas de synchronisation, càd qui sont "autonomes"
    sync_loops = {} #les cycles qui ont des synchronisations, regroupés par canal de synchronisation. 
    # ici sync_loops est un dico avec en clef le nom du canal, et en valeur la liste des cycles associés
    

    for c in all_cycles:
        if not c['syncs']:
            independent_loops.append(c)
        else:
            for sync in c['syncs']:
        
                base_chan = sync.replace('!', '').replace('?', '').split('[')[0].strip()
                sync_loops.setdefault(base_chan, []).append(c)

    # SI un cycle est synchronisé avec un autre qui est non zeno, il est aussi non zeno.
    # Donc si un cycle est synchronisé, tout les autres cycles synchronisés avec lui sur un meme channel sont aussi non zeno (d'où l'utilité de sync_loops !)
    # --- Step 4: Return unsafe loops ---
    
    unsafe_independent = [c for c in independent_loops if not c['is_snz']] # les loops indep qui ne passent pas la condition suffisante (càd qui sont potentiellement zeno)

    #Premier affichage des résultats sur les cycles indépendants
    if unsafe_independent:
        print("[!] Potentially Unsafe Independent Loops :")
        for i, c in enumerate(unsafe_independent):
            print(f"  Loop {i+1} in Template '{c['template']}':")
            for t in c['transitions']:
                src_name = c['locations_dict'].get(t['src'], {}).get('name', t['src'])
                tgt_name = c['locations_dict'].get(t['tgt'], {}).get('name', t['tgt'])
                print(f"    - [{src_name} -> {tgt_name}] Guard: '{t['guard']}', Update: '{t['assignment']}'")
            print()
    else:
        print("No unsafe independent loops found.\n")

    #Maintenant sur les cycles synchronisés
    found_unsafe_sync = False
    print("[!] Checking Synchronized Sets:")
    for chan, loops in sync_loops.items():
            # A set is potentially unsafe if NO loop in it is strongly non-zeno
            if all(not c['is_snz'] for c in loops):
                found_unsafe_sync = True
                print(f"\n [ZENO WARNING] Unsafe channel: '{chan}'")
                print(f"   (No loop in this group satisfies the sufficient Non-Zeno condition)")
                print("-" * 60)
                
                for c in loops:
                    print(f"     Template: {c['template']}  [SNZ: {c['is_snz']}]")
                    print(f"      Loop path ({len(c['transitions'])} transitions):")
                    
                    for t in c['transitions']:
                        src_name = c['locations_dict'].get(t['src'], {}).get('name', t['src'])
                        tgt_name = c['locations_dict'].get(t['tgt'], {}).get('name', t['tgt'])
                        
                        guard_str = f"Guard: {t['guard']}" if t['guard'] else "Guard: (none)"
                        update_str = f"Update: {t['assignment']}" if t['assignment'] else "Update: (none)"
                        sync_str = f"Sync: {t['sync']}" if t['sync'] else "Sync: (none)"
                        
                        is_target_sync = t['sync'] and chan in t['sync']
                        marker = " [Channel Sync]" if is_target_sync else ""
                        
                        print(f"        • [{src_name} --> {tgt_name}]{marker}")
                        print(f"          {sync_str} | {guard_str} | {update_str}")
                    print() 
                print("=" * 60)
            
    if not found_unsafe_sync:
        print(" No unsafe synchronized sets found.\n")
        
    if not unsafe_independent and not found_unsafe_sync:
        print(">>> CONCLUSION: The system is SAFE from Zeno behaviors, based on sufficient conditions!")
    else:
        print(">>> CONCLUSION: The system may have potential Zeno behaviors (it does not satisfy the sufficient conditions).")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        analyze(sys.argv[1])
    else:
        print("Usage: python zeno_checker_robust.py <model.xml>")