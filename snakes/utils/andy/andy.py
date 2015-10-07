###############################################################################
## AUXILIARY FUNCTIONS ########################################################

def clockt(obligatory, name, ls, us, lambdas, deltas, inputlist, D):
    '''This function computes the action of clock + decay + obligatory
    activities.
        obligatory = set of obligatory activities
        name = entity concerned
        ls = ls of entity
        us = us of entity
        lambdas = lambdas of entity
        deltas = list of the decays duration of entity
        inputlist = tuples for all other entities'''

    #print (obligatory, name, ls, us, lambdas, deltas, inputlist,D)
    l1=ls
    u1=us
    lambda1=[]

    # progression of time in lambda
    for i in range(0,len(lambdas)):
        lambda1.append(min(lambdas[i]+1, D))

    # progression of time for u (only for bounded levels)
    if deltas[ls] <> 0:
        u1=us+1

    # decay
    if us+1 > deltas[ls]:
        l1 = max(0, ls -1)
        u1 = 0

    # search of obligatory activities where entity name is in results
    act = []
    for alpha in range(0, len(obligatory)):
        obname = 'ob'+str(alpha)
        if name in obligatory[alpha][2] \
       and inputlist[obname]>= obligatory[alpha][3]:
            act.append(obligatory[alpha])

    # computation of the effect on entity name
    for alpha in range(0, len(act)):
        # check if the obligatory activity is enabled or not
        check = 0
        activators = act[alpha][0]
        for ent in activators:
            t = inputlist[ent]
            if t[0] >= activators[ent] \
           and t[2][activators[ent]] >= act[alpha][3]:
               check = 1
        inhibitors = act[alpha][1]
        for ent in inhibitors:
            t = inputlist[ent]
            if t[0] < inhibitors[ent] \
           and t[2][inhibitors[ent]] >= act[alpha][3]:
               check = 1
        # if enabled compute the effect
        if check:
            z = act[alpha][2][name]
            l1 = max(0, min(l1 + z, len(lambda1)-1))
            u1 = 0

    # update lambda with the proper dates
    temp = l1 - ls
    if temp > 0 :
        for i in range(ls+1,l1):
            lambda1[i]=0
    if temp < 0:
        for i in range(l1+1,ls):
            lambda1[i]=0

    return (l1, u1, tuple(lambda1))


def clockbetat (obligatory, name, w, inputlist,D) :
    '''This function computes the action of clock on obligatory activities
    places.
        obligatory = set of obligatory activities
        name = obligatory activity under consideration
        w = current value
        inputlist = tuples for all other entities'''

    check = 0
    activators = obligatory[name][0]
    for ent in activators:
        t = inputlist[ent]
        if t[0] >= activators[ent] \
       and t[2][activators[ent]] >= obligatory[name][3]:
           check = 1
    inhibitors = obligatory[name][1]
    for ent in inhibitors:
        t = inputlist[ent]
        if t[0] < inhibitors[ent] \
       and t[2][inhibitors[ent]] >= obligatory[name][3]:
           check = 1
    # if enabled compute the effect
    if check and w >= obligatory[name][3]:
        return(0)
    else:
        return(min(w+1, D))

def potentialt (name, lp, up, lambdap, R) :
    '''This function computes the action on an entity of a potential activity.
            name = entity under consideration
            lp, up, lambdap = its values
            R = set of results of the activity'''

    #print (name, lp, up, lambdap, R)
    # is entity a result?
    if name in R:
        lambda2 = list(lambdap)
        levelp = max(0,min(len(lambdap)-1, lp+R[name]))
        change = levelp-lp
        if change > 0:
            for i in range(lp+1,levelp+1):
                lambda2[i]=0
        if change < 0:
            for i in range(levelp+1,lp+1):
                lambda2[i]=0
        return (levelp, 0, tuple(lambda2))
    else:
        return (lp, up, lambdap)

## END ########################################################################
###############################################################################


###############################################################################
## MAIN #######################################################################
def andy2snakes(snk, entities, potential, obligatory):
    # compute maximal duration of activities
    D=0
    for alpha in potential : D = max(D, alpha[3])

    for alpha in obligatory : D = max(D, alpha[3])

    n = snk.PetriNet('andy')

    n.globals["obligatory"] = obligatory
    n.globals["D"] = D
    n.globals["clockt"] = clockt
    n.globals["clockbetat"] = clockbetat
    n.globals["potentialt"] = potentialt

    ################# Places for entities
    for i in range(0,len(entities)):
        name=entities[i][0]
        level = entities[i][1]
        deltas = entities[i][2]
        vector = [0]*len(deltas)
        n.add_place(snk.Place(name, [(level,0, tuple(vector))]))

    ################# clock transition
    inputlist = dict()
    n.globals["inputlist"] = inputlist

    n.add_transition(snk.Transition('tc'))


    # connect all obligatory clocks
    for i in range(0,len(obligatory)):
        # transition name
        obname = 'ob'+str(i)
        # for every obligatory activity connect corresponding place to clock
        n.add_place(snk.Place('p'+obname, [0]))
        n.add_input('p'+obname, 'tc', Variable('w'+obname))
        inputlist.update({obname:'w'+obname})


    # all entities are connected
    for i in range(0,len(entities)):
        name=entities[i][0]
        deltas = entities[i][2]
        n.globals["deltas"+name] = deltas
        n.globals[name] = name
        n.add_input(name, 'tc', snk.Tuple([snk.Variable('l'+name), snk.Variable('u'+name), snk.Variable('lambda'+name) ]))
        inputlist.update({name:['l'+name, 'u'+name, 'lambda'+name ]})



    for i in range(0,len(entities)):
        name=entities[i][0]
        n.add_output(name, 'tc', snk.Expression("clockt(obligatory,"+name+",l"+name+',u'+name+',lambda'+name+',deltas'+name+',inputlist,D)'))


    for i in range(0,len(obligatory)):
        obname = 'ob'+str(i)
        # for every obligatory activity connect corresponding place to clock
        n.add_output('p'+obname, 'tc', snk.Expression("clockbetat(obligatory,"+str(i)+',w'+obname+',inputlist,D)'))


    ## potential activities
    for i in range(0,len(potential)):
        # transition name
        trname = 'tr'+str(i)

        # for every potential activity connect corresponding place to clock
        n.add_place(snk.Place('p'+trname, [0]))
        n.add_input('p'+trname, 'tc', snk.Variable('w'+trname))
        n.add_output('p'+trname, 'tc', snk.Expression('min(D,w'+trname+'+1)'))


        activators = potential[i][0]
        inhibitors = potential[i][1]
        results = potential[i][2]
        #print results
        n.globals["results"+trname] = results
        duration = potential[i][3]

        # compute entities involved in the activity
        nameactivators = activators.keys()
        nameinhib = inhibitors.keys()
        nameresults = results.keys()
        names = []
        # check they appear only once
        for i in nameactivators : names.append(i)
        for i in nameinhib:
            if not (i in activators) : names.append(i)
        for i in nameresults:
            if not ( (i in activators) or (i in inhibitors)) : names.append(i)

        # compute guard of the activity
        # activity may be executed once every dur
        guard = 'w>='+str(duration)

        # activators
        for j in range(0,len(nameactivators)) :
            spec = nameactivators[j]
            level = str(activators[nameactivators[j]])
            guard += ' and l'+spec+'>= '+ level + ' and lambda' +spec+'['+level+']>='+str(duration)

        # inhibitors
        for j in range(0,len(nameinhib)) :
            spec = nameinhib[j]
            level = str(inhibitors[nameinhib[j]])
            guard += ' and l'+spec+'< '+ level + ' and lambda' +spec+'['+level+']>='+str(duration)

        n.add_transition(snk.Transition(trname, snk.Expression(guard)))
        n.add_input('p'+trname, trname, snk.Variable('w'))
        n.add_output('p'+trname, trname, snk.Expression('0'))

        # arcs of the transition from and to involved entities
        for j in range(0,len(names)) :
            n.add_input(names[j], trname, snk.Tuple([snk.Variable('l'+names[j]), snk.Variable('u'+names[j]), snk.Variable('lambda'+names[j]) ]))
            n.add_output(names[j], trname, snk.Expression("potentialt(" +names[j]+",l"+names[j]+',u'+names[j]+',lambda'+names[j]+', results'+trname+')'))

    return n

######## depict Petri net
def draw_net(net, out_name='repress'):
    net.draw(out_name+'.ps')

def draw_stategraph(snk, net, entities_names, out_name='repressgraph',
                    with_dot=True):
    def node_attr (state, graph, attr) :
        marking = graph[state]
        attr["label"] = ":".join( str(list(marking(s))[0][0])
                                  for s in entities_names )
    def edge_attr (trans, mode, attr) :
        attr["label"] = trans.name

    s = snk.StateGraph(net)
    s.build()

    s.draw(out_name+'.ps', node_attr=node_attr, edge_attr=edge_attr,
           engine='dot')

    if with_dot:
        g = s.draw(None, node_attr=node_attr, edge_attr=edge_attr,
                   engine='dot')
        with open(out_name+".dot", "w") as out:
            out.write(g.dot())
        g.render(out_name+"-layout.dot", engine="dot")

if __name__=='__main__':
    import snakes.plugins
    snakes.plugins.load(['gv', 'ops'], 'snakes.nets', 'snk')

    # entities: tuple of name of the entities, initial level, tuple of decays 0
    #           denotes unbounded decay (omega)
    # examples:
    #   entities = ( ('B',4, (0,2,2,2,3)), ('P',0, (0,0)), ('C',0, (0,0)),
    #                ('G',0, (0,0)) )
    #   entities = ( ('Sugar',1, (0,2)), ('Aspartame',0, (0,2)),
    #                ('Glycemia',2, (0,2,2,2)), ('Glucagon',0, (0,2)),
    #                ('Insulin',0,(0,2,2)) )

    entities = ( ('s1',0, (0,1)), ('s2',0, (0,1)), ('s3',0, (0,1)) )

    # Activities: Tuple of (activators, inhibitors, results, duration)
    #             activators, inhibitors are dictionaries of pairs
    #                                                           (entity, level)
    #             results are dictionaries of pairs (entity, +z)

    # potential activities examples:
    #   potential = ( (dict([('P',0)]),dict([('P',1)]),dict([('P',1)]),0),
    #                 (dict([('P',1)]),dict(),dict([('P',-1)]),0),
    #                 (dict([('C',0)]),dict([('C',1)]),dict([('C',1)]),0),
    #                 (dict([('C',1)]),dict(),dict([('C',-1)]),0),
    #                 (dict([('G',0)]),dict([('G',1)]),dict([('G',1)]),0),
    #                 (dict([('G',1)]),dict(),dict([('G',-1)]),0) )
    #   potential = ( (dict([('Sugar',1)]),dict(),
    #                    dict([('Insulin',1),('Glycemia',1)]),0),
    #                 (dict([('Aspartame',1)]),dict(),dict([('Insulin',1)]),0),
    #                 (dict(),dict([('Glycemia',1)]),dict([('Glucagon',1)]),0),
    #                 (dict([('Glycemia',3)]),dict(),dict([('Insulin',1)]),0),
    #                 (dict([('Insulin',2)]),dict(),dict([('Glycemia',-1)]),0),
    #                 (dict([('Insulin',1),('Glycemia',3)]), dict(),
    #                    dict([('Glycemia',-1)]),0),
    #                 (dict([('Insulin',1)]),dict([('Glycemia',2)]),
    #                    dict([('Glycemia',-1)]),0),
    #                 (dict([('Glucagon',1)]),dict(),dict([('Glycemia',+1)]),0)
    #               )

    potential = ( (dict(), dict([('s1',1)]), dict([('s2',1)]), 1),
                  (dict(), dict([('s2',1)]), dict([('s3',1)]), 1),
                  (dict(), dict([('s3',1)]), dict([('s1',1)]), 1) )

    # obligatory activities examples:
    #   obligatory = ( (dict([('P',1)]),dict(),dict([('B',1)]),1),
    #                  (dict([('C',1)]),dict(),dict([('B',-1)]),3),
    #                  (dict([('G',1)]),dict(),dict([('B',-2)]),3))

    obligatory = ()

    net = andy2snakes(snk, entities, potential, obligatory)
    draw_net(net, out_name="repress")
    draw_stategraph(snk, net, ("s1", "s2", "s3"), out_name="repressgraph")

