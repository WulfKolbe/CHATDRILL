

That minimum is the tropical determinant (7.5) of the matrix {{NonLinearAlgebra_FO0689||FO}} : 
Proposition 7.9. The tropical determinant solves the assignment problem. 
In the assignment problem we seek the minimum over {{NonLinearAlgebra_FO0753||FO}} quantities.  This appears to require exponentially many operations. However, there is  a polynomial-time method, with run time {{NonLinearAlgebra_FO1424||FO}}, known as the Hungarian  Algorithm. This algorithm maintains a price for each job and a partial  assignment of workers and jobs. At each iteration, an unassigned worker is  chosen and a shortest augmenting path from him to the set of jobs is chosen.