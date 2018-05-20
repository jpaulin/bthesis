# CPM for software delivery

Original article from Jukka Paulin
2018

Background

The delivery process for software has to do with
providing value to customer in prompt, optimal way.
Traditional 1990s and early 2000 project delivery
methods failed sometimes drastically due to 3 main 
visible reasons:
- excess timetables ("timetable lapses")
- inadequate features delivered in the end
- excess budgets as a result of timetable lapses

The Critical path is a well-known approach to project
work. A project often has that part of the deliverables
that are truly "important", and it has then "others"
that could be omitted or delivered iteratively, later on.

Software, just like other projects, has components
that can have dependency. Software delivery has often
been compared to being analogous to building a house.

## Software to manage making software?

Analysis
Proposal
Learning
Individuals in projects
Cross-tamination

### Cross-tamination

Individuals work in various load, so 1 person working
in project X in 2017 may perform differently when that
similar kind of project would occur a year later.

## Critical path management?

In this paper, we assume that Software is done with two ingredients:

Features
Tasks

There is a little known hazard in Agile development where
software is being developed actually *without* "Features" - ie.
with almost zero planning. Agile manifesto says that 
to counter the waterfall -era hazards, minimal overhead
work should be dedicated to up-front planning.

### Features
Features are the *design level artefacts* of a software project. 
They can be stories, spec, etc. Whatever you call 
Essentially, features are human-readable specs of what we're doing.

Tasks are technical memos of the specific
things that will be implemented either as contracts,
administrative operations (devops), or software development.

Converting Features to Tasks

The f->T conversion is critical

This yet does not indulge the nodes with path information.
Path information comes as edges. Nodes are connected
by directional edges. A directional edge ^= completion of the 
Tasks' content.

Ie. if there are 4 tasks 

A = Platform setup: installations and so on
B = Initial view creation in HTML
C = Making CSS (styling) for the app
D = Documenting (devops)

Relative importance algorithm (RIA)

For CPM to work, it should advise on what is the next
most critical sub-task. 
Tasks can have buckets. Popping the bucket's topmost element
means that a sub-task is marked "Complete". 

Here the dependencies of Tasks will be A:0, B:[A]
So B depends on A being completed. A can be done independently
at discretion (on its own viewpoint). But in practice
A will become the most crucial node, since it is the
first. 

Extra: Clone-ability (automation)
"Distinguishing what is the same, 
versus: what changes."
