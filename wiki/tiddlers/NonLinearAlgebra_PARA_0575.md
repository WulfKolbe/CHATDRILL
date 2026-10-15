
we refer to as independent sets. These are of course assumed to satisfy  certain axioms. 

A first observation is that whenever we have an independent set {{NonLinearAlgebra_FO2508||FO}},  it is reasonable to assume that every subset of {{NonLinearAlgebra_FO0038||FO}} is also independent. We  obtain the first axiom of a matroid for the family {{NonLinearAlgebra_FO2509||FO}} : 
1. If {{NonLinearAlgebra_FO2510||FO}} and {{NonLinearAlgebra_FO2511||FO}}, then {{NonLinearAlgebra_FO2512||FO}}. 

What we defined so far is a very important object in mathematics: simplicial  complex. Another observation is that we would like {{NonLinearAlgebra_FO2509||FO}} to be nonempty, or  equivalently we want the empty set to be independent: 
2. We have {{NonLinearAlgebra_FO2513||FO}}. 

It turns out that to obtain a matroid we need just one more axiom. To mo tivate it we make a following observation. Whenever we have finite linearly  independent subsets {{NonLinearAlgebra_FO2514||FO}} of a vector space {{NonLinearAlgebra_FO0317||FO}}, if {{NonLinearAlgebra_FO2515||FO}}, then we may  extend {{NonLinearAlgebra_FO0038||FO}} by an element of {{NonLinearAlgebra_FO2516||FO}}, in such a way that {{NonLinearAlgebra_FO2517||FO}} is still linearly  independent. This simple observation is precisely what we need to get the  last axiom for the family {{NonLinearAlgebra_FO2509||FO}} : 
3. If {{NonLinearAlgebra_FO2518||FO}} and {{NonLinearAlgebra_FO2515||FO}} then there exists {{NonLinearAlgebra_FO2516||FO}} such that {{NonLinearAlgebra_FO2519||FO}}. 

Definition 13.1. A matroid is a family of subsets {{NonLinearAlgebra_FO2509||FO}} satisfying Axioms {{NonLinearAlgebra_FO2520||FO}}. 
Exercise 1 asks to prove that the following structures are matroids: 
Example 13.2. - (Representable/Realizable matroid) Let {{NonLinearAlgebra_FO0317||FO}} be a  vector space over an arbitrary field {{NonLinearAlgebra_FO0961||FO}}. Let {{NonLinearAlgebra_FO2521||FO}} be a nonempty,  finite subset. We define {{NonLinearAlgebra_FO2509||FO}} to be the family of subsets of {{NonLinearAlgebra_FO2506||FO}} that  are linearly independent. We say that the matroid is representable  over {{NonLinearAlgebra_FO0961||FO}}. In coordinates, {{NonLinearAlgebra_FO2522||FO}} and we may identify the set {{NonLinearAlgebra_FO2506||FO}} as  an {{NonLinearAlgebra_FO2523||FO}} matrix. 
- (Graphic matroid) Let {{NonLinearAlgebra_FO1161||FO}} be a graph with edge set {{NonLinearAlgebra_FO2506||FO}}. Let {{NonLinearAlgebra_FO2509||FO}} be the  family of those subsets of {{NonLinearAlgebra_FO2506||FO}} that do not contain a cycle. Equiva lently {{NonLinearAlgebra_FO2509||FO}} is the family of forests in {{NonLinearAlgebra_FO1161||FO}}. 
- (Algebraic matroid) Let {{NonLinearAlgebra_FO2524||FO}} be an arbitrary field extension.  Let {{NonLinearAlgebra_FO2506||FO}} be a finite subset of {{NonLinearAlgebra_FO0001||FO}}. Let {{NonLinearAlgebra_FO2509||FO}} be the family of subsets of {{NonLinearAlgebra_FO2506||FO}}  that are algebraically independent over {{NonLinearAlgebra_FO0961||FO}}. 
- (Uniform matroid) Let {{NonLinearAlgebra_FO2506||FO}} be a finite set and {{NonLinearAlgebra_FO2525||FO}}. Let {{NonLinearAlgebra_FO2509||FO}} be the  family of subsets of cardinality at most {{NonLinearAlgebra_FO0592||FO}}. This matroid is denoted  by {{NonLinearAlgebra_FO2526||FO}} or {{NonLinearAlgebra_FO2527||FO}}. 

Matroids are known for having many equivalent definitions, depending  on the point of view on the matroid. For example, due to the first axiom  to determine a matroid we do not have to know all independent sets, just