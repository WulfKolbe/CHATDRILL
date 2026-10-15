## 10.2. Schur-Weyl Duality

 

In this section we present a beautiful connection between finite groups - {{NonLinearAlgebra_FO1422||FO}}  and Lie groups - {{NonLinearAlgebra_FO2157||FO}} or {{NonLinearAlgebra_FO2116||FO}}. This is the Schur-Weyl duality. We refer  readers interested in the topic to {{NonLinearAlgebra_FO2158||FO}}, Chapter 4]. 

Before stating it let us go back to irreducible representations of {{NonLinearAlgebra_FO1422||FO}}. Their  characters form a basis of class functions. Hence the number of irreducible  representations equals the number of conjugacy classes. Each conjugacy  class can be encoded by lengths of cycles in a decomposition of a permutation  into cycles. These can be further represented by a Young diagram with {{NonLinearAlgebra_FO0015||FO}}  boxes: the first row represents the length of the longest cycle, the last of the  shortest. Thus, the number of irreducible representations of {{NonLinearAlgebra_FO1422||FO}} equals the  number of Young diagrams with {{NonLinearAlgebra_FO0015||FO}} boxes. 

Example 10.22. For {{NonLinearAlgebra_FO0200||FO}} we have three conjugacy classes: 
- Identity {{NonLinearAlgebra_FO2159||FO}} with the Young diagram {{NonLinearAlgebra_FO2160||FO}} 
- Transpositions, e.g. (12)(3) with the Young diagram ; 
- 3-cycles, e.g. (123) with the Young diagram □ . 

We shall exhibit a natural bijection between Young diagrams with {{NonLinearAlgebra_FO0015||FO}}  boxes and irreducible representations of {{NonLinearAlgebra_FO1422||FO}}. Before we see how to construct  it, let us assume that to each such Young diagram {{NonLinearAlgebra_FO0387||FO}} we can associate a  representation {{NonLinearAlgebra_FO2161||FO}} of {{NonLinearAlgebra_FO1422||FO}}. 

Fix a vector space {{NonLinearAlgebra_FO2162||FO}} and consider the {{NonLinearAlgebra_FO0015||FO}}-fold tensor product {{NonLinearAlgebra_FO2163||FO}}. There  are two groups acting on it: {{NonLinearAlgebra_FO2135||FO}} - on each factor - and {{NonLinearAlgebra_FO1422||FO}} - by permuting  factors. Schur-Weyl duality provides a simultaneous decomposition of the  space of tensors with respect to both groups. 

Theorem 10.23 (Schur-Weyl duality). Let {{NonLinearAlgebra_FO2162||FO}} be a vector space of dimension  at least {{NonLinearAlgebra_FO0015||FO}}. Then