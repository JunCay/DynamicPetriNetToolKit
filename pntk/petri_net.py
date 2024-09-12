from .elements import *
import numpy as np
import uuid
import csv
import ast

class ColoredPetriNet():
    def __init__(self, name):
        self.id = uuid.uuid4()
        self.name = name
        self.places = dict()
        self.transitions = dict()
        self.arcs = dict()
        self.adj = dict()
        self.name_node = dict()
        self.id_name = dict()
        self.debug = False
        self.marking_types = list()
        self.update_ready_transition()
        
    def __str__(self):
        res = []
        for p in self.places.values():
            res.append({p.name: p.marking})
        return str(res)
        
        
    def add_node(self, node):
        """
        Add node to the petri net.
        Then update the ready transition list.
        Args:
            node (Transition): The transition to be added.
            node (Place): The place to be added.
        Returns:
            None
        """
        if isinstance(node, Place):
            self.places[node.id] = node
            self.name_node[node.name] = node
            self.id_name[node.id] = node.name
        elif isinstance(node, Transition):
            self.transitions[node.id] = node
            self.name_node[node.name] = node
            self.id_name[node.id] = node.name
        else:
            if self.debug:
                print("Node adding failed")
        self.update_ready_transition()
    
    def add_arc(self, node1, node2):
        """
        Add an arc to the petri net. Link TtoP or PtoT.
        Then update the ready transition list.

        Args:
            node1 (Transition / Place)
            node2 (Place / Transition)
        Returns:
            None 
        """
        arc = Arc(node1, node2)
        self.arcs[arc.id] = arc
        node1.outs[node2.id] = node2
        node1.out_arcs[arc.id] = arc
        node2.ins[node1.id] = node1
        node2.in_arcs[arc.id] = arc
        self.name_node[arc.name] = arc
        self.id_name[arc.id] = arc.name
        self.adj[(node1.id, node2.id)] = arc
        self.update_ready_transition()
    
    def init_by_csv(self, path):
        """
        Init the petri net by a csv file.

        Args:
            path (str): The path of the csv file.
        """
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.strip(): v.strip() for k, v in row.items()}
                command = row['command']
                args = ast.literal_eval(row['args'])
                
                if command == 'MADP':
                    # Add Place Node
                    self.add_node(Place(args[0], ast.literal_eval(args[1])))
                elif command == 'MADT':
                    # Add Transition Node
                    self.add_node(Transition(args[0], None, ast.literal_eval(args[1])))
                elif command == 'MADA':
                    # Add Arc
                    self.add_arc(self.name_node[args[1]], self.name_node[args[2]])
                    
                    
    
    @property
    def tokens(self):
        """
        Get the tokens of all places in the petri net.

        Returns:
            List[Dict]: The tokens of all places in the petri net.
        """
        res = []
        for p in self.places.values():
            res.append({'id':p.id, 'tokens':p.tokens, 'marking':p.marking})
        return res
        
    @property 
    def ready_transition(self):
        """
        Return the ready transition in the petri net.

        Returns:
            List[Transition]: by transition nodes.
        """
        res = []
        for t in self.transitions.values():
            if self.transition_ready_check(t):
                res.append(t)
        return res
        
    def update_ready_transition(self):
        """
        Update the ready transition in the petri net to transition nodes.
        """
        for t in self.transitions.values():
            self.transition_ready_check(t)


    def transition_ready_check(self, transition:Transition):
        """
        Check if the input transition is ready to fire.

        Args:
            transition (Transition): The transition to be checked.

        Returns:
            Boolean: if the transition is ready to fire.
        """
        for arc in transition.in_arcs.values():
            if not self.arc_ready(arc):
                transition.status = 'unready'
                return False
        transition.status = 'ready'
        return True
    
    def arc_ready(self, arc:Arc):
        """
        Check if the input arc is ready to fire. 
        Arc stresses the requirement of the transition.

        Args:
            arc (Arc): The arc to be checked.

        Returns:
            Boolean: if the arc is ready to fire.
        """
        if arc.direction == 'PtoT':
            for k in arc.annotation.keys():
                if arc.node_in.marking[k] - arc.annotation[k] >= 0:
                    return True
            return False
        else:
            return False
        
    def fire_transition(self, transition:Transition):
        """
        Fire the input transition. Then update the ready transition list.
        Used when the net is not a timed net.
        
        Args:
            transition (Transition): The transition to be fired.

        Returns:
            Boolean: if the transition is successfully fired.
        """
        # print(f"firing transition: {transition.name}")
        if transition not in self.transitions.values():
            if self.debug:
                print(f"Transition not found in current petri net")
            return False
        if not self.transition_ready_check(transition):
            if self.debug:
                print(f"Transition not found in current petri net")
            return False
        for arc in self.transitions[transition.id].in_arcs.values():
            for k in arc.node_in.marking.keys():
                arc.node_in.marking[k] -= arc.annotation[k]
        for arc in self.transitions[transition.id].out_arcs.values():
            for k in arc.node_out.marking.keys():
                arc.node_out.marking[k] += arc.annotation[k]

        self.update_ready_transition()
        return True

    def on_fire_transition(self, transition:Transition):
        """
        Set the transition to firing status.

        Args:
            transition (Transition): The transition to be started.

        Returns:
            Boolean: if the transition is successfully started.
        """
        # print(f"on firing transition: {transition.name}")
        if transition not in self.transitions.values():
            if self.debug:
                print(f"Transition not found in current petri net")
            return False
        if not self.transition_ready_check(transition):
            if self.debug:
                print(f"Transition not found in current petri net")
            return False
        if transition.work_status == 'firing':
            if self.debug:
                print(f"Transition is already firing")
            return False
        
        for arc in self.transitions[transition.id].in_arcs.values():
            for k in arc.node_in.marking.keys():
                arc.node_in.marking[k] -= arc.annotation[k]
        transition.work_status = 'firing'
        transition.time = transition.consumption
        return True
    
    def tick(self, dt):
        """
        Tick the time of all transitions.

        Args:
            dt (float): delta time

        Returns:
            List[str]: The names of the finished transitions
        """
        changed = []
        for transition in self.transitions.values():
            f = transition.tick(dt)
            if f:
                changed.append(transition.name)
                for arc in transition.out_arcs.values():
                    for k in arc.node_out.marking.keys():
                        arc.node_out.marking[k] += arc.annotation[k]
                transition.work_status = 'unfiring'
                self.update_ready_transition()
        return changed

    def reset_net(self):
        """
        Reset the marking of all places in the net to initial marking.
        """
        for place in self.places.values():
            place.initialize()
        
    def get_marking_types(self):
        for p in self.places.values():
            for t in p.marking.keys():
                if t not in self.marking_types:
                    self.marking_types.append(t)
        return self.marking_types
    
    def print_adj(self):
        res = []
        res.append(['\\'])
        for i, key_from in enumerate(self.name_node.keys()):
            if isinstance(self.name_node[key_from], Place) or isinstance(self.name_node[key_from], Transition):
                res[0].append(key_from)
                res.append([key_from])
                for j, key_to in enumerate(self.name_node.keys()):
                    if isinstance(self.name_node[key_to], Place) or isinstance(self.name_node[key_to], Transition):
                        if ((self.name_node[key_from].id, self.name_node[key_to].id) in self.adj.keys()):
                            res[i+1].append(1)
                        else:
                            res[i+1].append(0)
        mat_str = 'identity petri net adjMatrix: \n'
        for i in range(len(res)):
            for j in range(len(res[0])):
                mat_str += str(res[i][j]) + '\t'
            mat_str += '\n'
        print(mat_str)
    # RL part
    def reset(self):
        """
        Reset the net to initial state
        """
        self.reset_net()
        self.update_ready_transition()
        
    def get_place_state(self):
        """
        Tobe overrided to customize the state of the petri net.

        Returns:
            np.ndarray: state matrix of places
        """
        marking_types = self.get_marking_types()
        place_state = np.zeros((len(self.places), len(marking_types)))
        for i, place in enumerate(self.places.values()):
            for mt in marking_types:
                if mt in place.marking.keys():
                    place_state[i, marking_types.index(mt)] = place.marking[mt]
        return place_state
    
    def get_transition_state(self):
        """
        Tobe overrided to customize the state of the petri net.

        Returns:
            _type_: _description_
        """
        trans_state = np.zeros(len(self.transitions))
        for i, transition in enumerate(self.transitions.values()):
            if transition.work_status == 'firing':
                if transition.consumption == 0:
                    trans_state[i] = 0.0
                else:
                    trans_state[i] = (transition.consumption - transition.time) / transition.consumption
            else:
                trans_state[i] = 0.0
        return trans_state
    
    def get_state(self):
        pass
    
    def step(self, action:Transition):
        pass