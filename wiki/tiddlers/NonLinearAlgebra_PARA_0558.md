## 12.3. Sums of Squares

 

Semidefinite programming can be used to model and solve arbitrary poly nomial optimization problems. The key to this is the representation of  nonnegative polynomials in terms of sums of squares, or, more generally,  the Real Nullstellensatz (cf. Chapter 6). We explain this for the simplest  scenario, namely the problem of unconstrained polynomial optimization. 

Let {{NonLinearAlgebra_FO2468||FO}} be a polynomial of even degree {{NonLinearAlgebra_FO2469||FO}}, and suppose that  {{NonLinearAlgebra_FO0029||FO}} attains a minimal real value {{NonLinearAlgebra_FO1581||FO}} on {{NonLinearAlgebra_FO0418||FO}}. Our goal is to compute {{NonLinearAlgebra_FO1581||FO}} and a  point {{NonLinearAlgebra_FO2470||FO}} such that {{NonLinearAlgebra_FO2471||FO}}. Minimizing a function is equivalent  to finding the best possible lower bound {{NonLinearAlgebra_FO0387||FO}} for that function. Our goal is  therefore equivalent to solving the following optimization problem: