class CycleException (ValueError):
   """
      Error thrown when adding an edge to a DAG would create a cycle.
   """
   def __init__ (self,start, end):
      super().__init__("Inserting edge from {} to {} creates cycle in graph.".format(start,end))

# inb4 "fuk dag"
class DirectedAcyclicGraph:
   """
      Implementation of a simple directed acyclic graph using two sets for edges and vertices.

      Vertex types can be any hashable object; edges are (start,end) pairs of vertices.
   """
   def __init__ (self):
      # set of vertices
      self.vertices = set()
      # set of edges
      self.edges = set()
      # bookkeeping dicts; used for forcing acyclic property
      # above[v] is the set of vertices x with a path from x to v
      self.above = {}
      # below[v] is th eset of vertices x with a path from v to x
      self.below = {}
      
   def addVertex (self, vertex):
      self.vertices.add(vertex)
      self.above[vertex] = set()
      self.below[vertex] = set()

   def roots (self):
      """
         Returns all roots of this dag; i.e., vertices with no incident edges.
      """
      return set(x for x in self.vertices if len(self.incident(x)) == 0)

   def incident (self, vertex):
      """
         Gets all edges incident on the given vertex.
      """
      output = set()
      for v2 in self.vertices:
         if (v2,vertex) in self.edges:
            output.add((v2,vertex))
      return output

   def addEdge (self, start, end):
      """
         Adds an edge from start to end, enforcing acyclic property.
      """
      if start and end in self.vertices:
         if end in self.above[start]:
            raise CycleException(start,end)
         # add the edge
         self.edges.add((start,end))
         # start and everything above it is now above end
         self.above[end].add(start)
         self.above[end] |= self.above[start]
         # end and everything below it is now below start
         self.below[start].add(end)
         self.below[start] |= self.below[end]
         # if an edge is above start, it is now above end and everything below it
         for vertex in self.above[start]:
            self.below[vertex].add(end)
            self.below[vertex] |= self.below[end]
         # if an edge is below end, it is now below start and everything above it
         for vertex in self.below[end]:
            self.above[vertex].add(start)
            self.above[vertex] |= self.above[start]      
      else:
         raise ValueError("Adding edge between nonexistent vertices.")

def dag_main ():
   dag = DirectedAcyclicGraph()
   for i in range(1,11):
      dag.addVertex(i)
   dag.addEdge(1,2)
   print("should be 1",dag.above[2])
   dag.addEdge(2,3)
   dag.addEdge(2,4)
   dag.addEdge(4,5)
   print("should be empty set",dag.above[1])
   print("should be 1,2,4",dag.above[5])
   print("should be 3,4,5",dag.below[2])
   try:
      dag.addEdge(5,1)
      print("You shouldn't see this.")
      print(dag.edges)
   except CycleException as e:
      print("should complain about cycles:",e)
   dag.addEdge(3,4)
   print("should be 1,2,3,4",dag.above[5])
   print("should be 1,6,7,8,9,10",dag.roots())
   dag.addEdge(7,1)
   print("should be 1,2,7",dag.above[3])

if __name__ == '__main__':
   dag_main()