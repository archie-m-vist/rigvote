import sys
import os.path
from dag import DirectedAcyclicGraph, CycleException
from vote import SerialPoller, pollers

class RankedPairsCalculator:
   def __init__ (self, poller, *args, **kwargs):
      super().__init__(*args,**kwargs)
      self.poller = poller
      self.pairs = []
      self.weights = {}

   def rankPairs (self):
      """
         Sorts pairs according to the information in the poller.
      """
      def key (matrix, pair):
         # majority is positive, we want larger ones first
         major = matrix[pair[0]][pair[1]]
         # minority is negative because we want the smaller ones first
         minor = -1*matrix[pair[1]][pair[0]]
         return (major,minor)

      self.pairs = [(x,y) for x in self.poller.candidates for y in self.poller.candidates if x != y]
      matrix = self.poller.voteMatrix()
      # reverse=true to indicate descending sort
      self.pairs.sort(key=lambda pair: key(matrix,pair), reverse=True)
      self.weights = { pair : key(matrix,pair) for pair in self.pairs }
      self.pairs = [pair for pair in self.pairs if self.weights[pair][0] > -1*self.weights[pair][1]]

   def getSingleWinner (self):
      self.rankPairs()
      graph = DirectedAcyclicGraph()
      for candidate in self.poller.candidates:
         graph.addVertex(candidate)
      for pair in self.pairs:
         try:
            graph.addEdge(*pair)
            print("Added edge ({} -> {}) to graph ({} for, {} against).".format(*pair,self.weights[pair][0], -1*self.weights[pair][1]))
         # ignore edges which would create a cycle
         except CycleException:
            print("Edge ({} -> {}) would create a cycle, skipping ({} for, {} against).".format(*pair,self.weights[pair][0], -1*self.weights[pair][1]))
      roots = graph.roots()
      return roots if len(roots) > 1 else roots.pop()

   def getOrderedList (self):
      self.rankPairs()
      candidates = set(self.poller.candidates)
      output = []
      while len(candidates) > 0:
         print("{} candidates remain.".format(len(candidates)))
         graph = DirectedAcyclicGraph()
         for candidate in candidates:
            graph.addVertex(candidate)
         for pair in self.pairs:
            try:
               graph.addEdge(*pair)
               print("Added edge ({} -> {}) to graph ({} for, {} against).".format(*pair,self.weights[pair][0], -1*self.weights[pair][1]))
            # ignore edges which would create a cycle
            except CycleException:
               print("Edge ({} -> {}) would create a cycle, skipping ({} for, {} against).".format(*pair,self.weights[pair][0], -1*self.weights[pair][1]))
               continue;
         roots = graph.roots()
         winner = roots if len(roots) > 1 else roots.pop()
         # note winner in output
         output.append(winner)
         print("Place {}: {}\n".format(len(output), winner))
         # remove winner from list of candidates
         candidates.remove(winner)
         # remove pairs involving the winner from the ranking
         self.pairs = [x for x in self.pairs if winner not in x]
      return output

   def detailedResults (self):
      lst = self.getOrderedList()
      for i in range(len(lst)):
         print("{}: {}".format(i+1,lst[i]))
         for j in range(i+1,len(lst)):
            try:
               weight = self.weights[(lst[i],lst[j])]
            except:
               continue
            print("   versus {}: {} for, {} against".format(lst[j],weight[0],-1*weight[1]))

def main ():
   if len(sys.argv) == 1 or sys.argv[1] == "test":
      print("Running Wikipedia example.")
      candidates = ["M","N","C","K"]
      votes = ""
      for i in range(42):
         votes += "M>N>C>K\n"
      for i in range(26):
         votes += "N>C>K>M\n"
      for i in range(15):
         votes += "C>K>N>M\n"
      for i in range(17):
         votes += "K>C>N>M\n"
      votes = votes[:-1]
      poller = SerialPoller(candidates=candidates,data=votes)
      calc = RankedPairsCalculator(poller)
      calc.detailedResults()
   else:
      filetype = os.path.splitext(sys.argv[1])[1][1:]
      poller = pollers[filetype](filename=sys.argv[1])
      calc = RankedPairsCalculator(poller)
      calc.detailedResults()

      input("Press Enter to continue.")



if __name__ == '__main__':
   main()