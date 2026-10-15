
(1) All {{NonLinearAlgebra_FO0015||FO}} eigenvalues of {{NonLinearAlgebra_FO0511||FO}} are positive real numbers. 
(2) All {{NonLinearAlgebra_FO1641||FO}} principal minors of {{NonLinearAlgebra_FO0511||FO}} are positive real numbers. 
(3) Every non-zero column vector {{NonLinearAlgebra_FO1266||FO}} satisfies {{NonLinearAlgebra_FO2403||FO}}. 

Here, by a principal minor we mean the determinant of any square submatrix  of {{NonLinearAlgebra_FO0511||FO}} whose set of column indices agree with its set of row indices. For the  empty set, we get the {{NonLinearAlgebra_FO2404||FO}} minor of {{NonLinearAlgebra_FO0511||FO}}, which equals 1 . Next there are the  {{NonLinearAlgebra_FO0015||FO}} diagonal entries of {{NonLinearAlgebra_FO0511||FO}}, which are the {{NonLinearAlgebra_FO0290||FO}} principal minors, and finally the  determinant of {{NonLinearAlgebra_FO0511||FO}}, which is the unique {{NonLinearAlgebra_FO0510||FO}} principal minor. Each of the  three conditions (1), (2) and (3) behaves as expected when we pass to the  closure. This is not obvious because the closure of an open semialgebraic set  {{NonLinearAlgebra_FO2405||FO}}, where {{NonLinearAlgebra_FO1267||FO}}, is generally smaller than the corresponding closed  semialgebraic set {{NonLinearAlgebra_FO2406||FO}}. 

Example 12.1. Let {{NonLinearAlgebra_FO2407||FO}}. The set {{NonLinearAlgebra_FO2405||FO}}  is the open halfplane above the line {{NonLinearAlgebra_FO2408||FO}} in {{NonLinearAlgebra_FO0307||FO}}. The closure of the set  {{NonLinearAlgebra_FO2405||FO}} is the corresponding closed halfplane. It is properly contained in  {{NonLinearAlgebra_FO2406||FO}} which also contains the origin {{NonLinearAlgebra_FO0628||FO}}. 

Luckily, no such thing happens with condition (2) for positive definite  matrices. 

Theorem 12.2. For a symmetric {{NonLinearAlgebra_FO0510||FO}} matrix {{NonLinearAlgebra_FO0511||FO}}, the following three con ditions are equivalent: 
(1') All {{NonLinearAlgebra_FO0015||FO}} eigenvalues of {{NonLinearAlgebra_FO0511||FO}} are nonnegative real numbers. 
(2') All {{NonLinearAlgebra_FO1641||FO}} principal minors of {{NonLinearAlgebra_FO0511||FO}} are nonnegative real numbers. 
(3') Every non-zero column vector {{NonLinearAlgebra_FO1266||FO}} satisfies {{NonLinearAlgebra_FO2409||FO}}. 
If this holds then {{NonLinearAlgebra_FO0511||FO}} is called positive semidefinite. The semialgebraic set  {{NonLinearAlgebra_FO2410||FO}} of positive semidefinite {{NonLinearAlgebra_FO0510||FO}} matrices is a full-dimensional closed con vex cone in {{NonLinearAlgebra_FO2411||FO}}. 

We use the notation {{NonLinearAlgebra_FO2412||FO}} to express that a symmetric matrix {{NonLinearAlgebra_FO0285||FO}} is  positive semidefinite. A spectrahedron {{NonLinearAlgebra_FO0174||FO}} is the intersection of the cone {{NonLinearAlgebra_FO2410||FO}}  with an affine-linear subspace {{NonLinearAlgebra_FO2413||FO}} of the ambient space {{NonLinearAlgebra_FO2411||FO}}. Hence,  spectrahedra are closed convex semialgebraic sets. 

A subspace {{NonLinearAlgebra_FO2413||FO}} of symmetric matrices is either given parametrically, or  as the solution set to an inhomogeneous system of linear equations. In the  equational representation, we write