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

