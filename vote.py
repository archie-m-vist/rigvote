from rigvote_util import isIterable

# vote exception classes
class InvalidCandidate (ValueError):
   def __init__ (self, candidates):
      if isIterable(candidates):
         super().__init__("Candidates {} are not valid in this election.".format(str(list(candidates))[1:-1]))
      else:
         super().__init__("Candidate {} is not valid in this election.".format(candidates))

class SameCandidate (ValueError):
   def __init__ (self, candidate):
      super().__init__("Candidate {} cannot run against themself.".format(candidate))

class Vote:
   def __init__ (self, *args, candidates, **kwargs):
      # pass extra args or kwargs to object
      super().__init__(*args, **kwargs)
      # store candidates
      self.candidates = set(candidates)
      # initialise votes
      self.votes = { candidate : set() for candidate in self.candidates }
      # serialised string vote; used by SerialVote to load saved votes, and generated by __str__ or __repr__.
      self.serial = None

   def checkCandidates (self, c1, c2 = None):
      """
         Runs sanity tests on candidates and raises appropriate exceptions.
      """
      if c1 not in self.candidates:
         if c2 is not None and c2 not in self.candidates:
            raise InvalidCandidate([c1,c2])
         else:
            raise InvalidCandidate(c1)
      elif c2 is not None and c2 not in self.candidates:
         raise InvalidCandidate(c2)
      if c1 == c2:
         raise SameCandidate(c1)

   def vote (self, winner, loser):
      """
         Marks down a vote between two candidates.
      """
      self.checkCandidates(winner,loser)
      self.votes[winner].add(loser)
      # data has changed so serial string is out of date and must be recalculated if needed
      self.serial = None

   def tally (self, candidateOne, candidateTwo):
      """
         Returns the preferred candidate out of candidateOne and candidateTwo, or None if no preference
         was given.
      """
      self.checkCandidates(candidateOne,candidateTwo)
      if candidateTwo in self.votes[candidateOne]: # candidateOne beats candidateTwo
         return candidateOne
      elif candidateOne in self.votes[candidateTwo]: # candidateTwo beats candidateOne
         return candidateTwo
      else: # no winner
         return None

   def __str__ (self):
      def merge (before, equal, after):
         # joins lists together; note that equal is appended, not extended, to allow for ties
         before.append(equal)
         before.extend(after)
         return before

      def helper (candidate, lst):
         before = []
         equal = set(candidate)
         after = []
         for other in lst:
            if candidate == other:
               continue;
            winner = self.tally(candidate,other)
            if winner == candidate:
               after.append(other)
            elif winner == other:
               before.append(other)
            elif winner is None:
               equal.add(other)
            else:
               raise Exception("You should never see this, go yell at Archie.")
         # split and merge the other lists if they're too large
         if len(before) > 1:
            before, be, ba = helper(before[0], before)
            before = merge(before,be,ba)
         if len(after) > 1:
            ab, ae, after = helper(after[0], after)
            after = merge(ab,ae,after)
         # return sorted lists
         return before, equal, after

      if self.serial is None:
         before, equal, after = helper(tuple(self.candidates)[0],self.candidates)
         ordered = merge(before,equal,after)
         self.serial = ""
         for value in ordered:
            if isIterable(value):
               temp = "=".join(sorted([str(x) for x in value]))
            else:
               temp = value
            self.serial += str(temp)
            if value != ordered[-1]:
               self.serial += ">"

      return self.serial

   def __repr__ (self):
      return "SerialVote(candidates={},data='{}')".format(self.candidates,str(self))

class Poller:
   def __init__ (self, candidates, *args, **kwargs):
      self.candidates = candidates
      self.votes = []

   def __str__(self):
      return "\n".join(list(self.candidates) + [str(vote) for vote in self.votes])

   def __repr__ (self):
      return "SerialPoller(data='{}')".format(str(self))

   def voteMatrix (self):
      """
         Returns a dict of dicts such that voteMatrix()[first][second] returns the number of votes that first beat second by.
      """
      polls = { candidate : {} for candidate in self.candidates }
      clist = list(self.candidates)
      for i in range(len(clist)):
         first = clist[i]
         # can't run against self
         polls[first][first] = None
         # calculate new races
         for j in range(i+1,len(clist)):
            second = clist[j]
            polls[first][second] = 0
            polls[second][first] = 0
            for vote in self.votes:
               winner = vote.tally(first,second)
               if winner is not None:
                  if winner == first:
                     polls[first][second] += 1
                  else:
                     polls[second][first] += 1

      return polls

class SerialVote (Vote):
   """
      Vote implementation handling a vote from a serialised Vote object.
      
      These shouldn't be invoked directly, instead simply pulling from a Vote object.
   """
   def __init__ (self, candidates, data, *args, **kwargs):
      # serialvote allows for absent candidates, so figure out who the vote actually mentions
      votes = data.split(">")
      candidates = self.candidatesInVote(votes)
      super().__init__(*args, candidates=candidates, **kwargs)
      temp=set(self.candidates)
      for vote in votes:
         if "=" in vote:
            vote = vote.split("=")
            temp -= set(vote)
            for candidate in vote:
               self.votes[candidate] |= temp
         else:
            temp.remove(vote)
            self.votes[vote] |= temp

   def candidatesInVote(self, vote):
      output = set()
      for position in vote:
         if "=" in position:
            output |= set(position.split("="))
         else:
            output.add(position)
      return output

class SerialPoller (Poller):
   """
      Implementation of a Poller that needs specified candidates and can read SerialVote objects; intended to be used for a repr of a Poller.

      Note that this class does not include a Vote implementation; SerialVote is made available in the main module.
   """

   def __init__ (self, data, *args, **kwargs):
      super().__init__(*args, **kwargs)
      for line in data.split("\n"):
         self.votes.append(SerialVote(candidates=self.candidates,data=line))

class GFormsPoller (Poller):
   class GFormsVote (Vote):
      """
         Vote implementation handling a vote from a line on a Google Forms grid result.

         Notably, this assumes that candidates are both:
          * All present in every vote.
          * Never given equal rank.
      """
      def __init__ (self, line, *args, **kwargs):
         """
            Initialises this Vote from a line from a Google Forms .csv file, format date,1st,2nd,3rd,...
         """
         # superclass constructor; initialises candidates and self.votes dict
         super().__init__(*args, **kwargs)
         # ignore the date value
         votes = line.split(",")[1:]
         candidates = list(self.candidates)
         ranks = {}
         # iterate across candidates
         for i in range(len(candidates)):
            first = candidates[i]
            ranks[first] = votes.index(first)
            for j in range(i+1,len(candidates)):
               second = candidates[j]
               if second not in ranks:
                  ranks[second] = votes.index(second)
               if ranks[first] < ranks[second]:
                  self.vote(first,second)
               else:
                  self.vote(second,first)

   def __init__ (self, filename, *args, **kwargs):
      with open(filename) as f:
         # read the file, stripping lines and ignoring column headers
         lines = [line.strip() for line in f.readlines()][1:]
         f.close()
      # gforms guarantees all candidates are on every line so we can just read them from the first vote
      candidates = lines[0].split(',')[1:]
      # pass candidates to poller class
      super().__init__(candidates=candidates, *args, **kwargs)
      # read lines into votes
      for line in lines:
         self.votes.append(GFormsPoller.GFormsVote(line=line,candidates=candidates))

def votepy_main ():
   l = ['a','b','c','d']
   temp = GFormsPoller.GFormsVote(line="ignoreme,a,c,b,d",candidates=l)
   print("should be a>c>b>d:",temp)
   temp = SerialVote(data="a>b=d>c",candidates=l)
   print("should be a>b=d>c:",temp)
   temp = GFormsPoller.GFormsVote(line="eyy,d,b,c,a",candidates=l)
   temp2 = eval(repr(temp))
   print("should be equal:",temp,temp2)
   temp = SerialVote(data="a=b>d",candidates=l)
   print("should be a=b>d:", temp)

if __name__ == '__main__':
   votepy_main()

pollers = {
   "csv" : GFormsPoller,
   "rvs" : SerialPoller
}