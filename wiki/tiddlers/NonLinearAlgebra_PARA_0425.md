
(2) Add the {{NonLinearAlgebra_FO1960||FO}} entry of the first matrix to the ( 2,2 ) entry and mul tiply by the {{NonLinearAlgebra_FO1958||FO}} entry of the second matrix. Put the result in the  {{NonLinearAlgebra_FO1960||FO}} entry and negated {{NonLinearAlgebra_FO1959||FO}} entry of the second partial result. 

Computing each partial result requires only one multiplication. Although  we improved on the number of multiplications, we increased the number  of additions (and subtractions) to 21 . Why should this be exciting? The  reason is that multiplication of {{NonLinearAlgebra_FO0286||FO}} matrices is not our final aim. 

We would like to multiply very large matrices. Consider two {{NonLinearAlgebra_FO1961||FO}}  matrices. How to multiply them? We may regard our matrices as {{NonLinearAlgebra_FO0286||FO}}  matrices with entries that are {{NonLinearAlgebra_FO1962||FO}} matrices and apply Strassen's Al gorithm! We will have to add a lot of {{NonLinearAlgebra_FO1962||FO}} matrices, but we only need  to perform seven mutliplications of such matrices. Further, these multipli cations may be done recursively applying the same algorithm, reducing to  multiplication of {{NonLinearAlgebra_FO1963||FO}} matrices, etc. Anyone who tried multiplying or  adding very large matrices knows that it is beneficial to trade mutliplication  even for many additions. This is in fact a theorem: the complexity of the  (optimal) algorithm to multiply matrices is governed by the rank of {{NonLinearAlgebra_FO1964||FO}}. 

The asymptotics of these quantities is measured by the constant 
{{NonLinearAlgebra_FO1965||FO}} the complexity of multiplying two {{NonLinearAlgebra_FO0510||FO}} matrices is {{NonLinearAlgebra_FO1966||FO}} 
{{NonLinearAlgebra_FO1967||FO}} of {{NonLinearAlgebra_FO1968||FO}}. 
This quantity is known as the exponent of matrix multiplication. The naive  algorithm shows that {{NonLinearAlgebra_FO1969||FO}}. However Strassen's Algorithm, as described  above, gives {{NonLinearAlgebra_FO1970||FO}}. As matrices are of size {{NonLinearAlgebra_FO1971||FO}}, we also know that {{NonLinearAlgebra_FO1972||FO}}. 

The central conjecture in this field says that the lower bound is attained: 
Conjecture 9.24. The constant {{NonLinearAlgebra_FO1973||FO}} is equal to two. 
The conjecture would imply that it is not much harder to multiply very  large matrices then to add them (or even output the result)! At this point  we note that our story is really relevant for scientific computing. Strassen's  Algorithm is implemented and used in practice to multiply large matrices. 

A careful reader might now have an idea how to proceed with a proof  of Conjecture 9.24. As Strassen looked at {{NonLinearAlgebra_FO0286||FO}} matrices, we should focus  on larger matrices, say {{NonLinearAlgebra_FO0035||FO}}. The disappointing fact is that despite many  attempts, no one knows either the rank or the border rank of the {{NonLinearAlgebra_FO1974||FO}}  tensor {{NonLinearAlgebra_FO1975||FO}}. For the current best estimates we refer to [33, 34, 35, 48. 

For each fixed {{NonLinearAlgebra_FO0015||FO}}, deciding if rank (resp. border rank) of {{NonLinearAlgebra_FO1964||FO}} is {{NonLinearAlgebra_FO1897||FO}} means  deciding if {{NonLinearAlgebra_FO1964||FO}} belongs to the image (resp. closed image) of a particular poly nomial map. Thus, the methods of Chapter 4 apply. However, as tensor  spaces are high-dimensional, such computations are impossible to carry out