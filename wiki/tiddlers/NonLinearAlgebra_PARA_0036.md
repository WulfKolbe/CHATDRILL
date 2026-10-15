
1.11. Since {{NonLinearAlgebra_FO0161||FO}}, there exists an element {{NonLinearAlgebra_FO0162||FO}} whose initial mono mial divides {{NonLinearAlgebra_FO0110||FO}}, say {{NonLinearAlgebra_FO0163||FO}}. Now, {{NonLinearAlgebra_FO0164||FO}} is a polynomial with  strictly smaller initial monomial. It lies in {{NonLinearAlgebra_FO0038||FO}} but it does not lie in the ideal  {{NonLinearAlgebra_FO0165||FO}}. This is a contradiction to the choice of {{NonLinearAlgebra_FO0029||FO}}. 

Corollary 1.14 (Hilbert's Basis Theorem). Every ideal {{NonLinearAlgebra_FO0038||FO}} in {{NonLinearAlgebra_FO0021||FO}} is finitely  generated. 

Proof. Fix any monomial order {{NonLinearAlgebra_FO0132||FO}}. By Proposition 1.12, the ideal {{NonLinearAlgebra_FO0038||FO}} has a  finite Gröbner basis {{NonLinearAlgebra_FO0154||FO}}. By Theorem 1.13, the finite set {{NonLinearAlgebra_FO0154||FO}} generates {{NonLinearAlgebra_FO0038||FO}}. 

Gröbner bases are not unique. If {{NonLinearAlgebra_FO0154||FO}} is a Gröbner basis of an ideal {{NonLinearAlgebra_FO0038||FO}} with  respect to a monomial order {{NonLinearAlgebra_FO0132||FO}} then so is every other finite subset of {{NonLinearAlgebra_FO0038||FO}} that  contains {{NonLinearAlgebra_FO0154||FO}}. In that sense, Gröbner bases differ from the bases we know from  linear algebra. The issue of minimality and uniqueness is addressed next. 

Definition 1.15. Fix {{NonLinearAlgebra_FO0038||FO}} and {{NonLinearAlgebra_FO0132||FO}}. A Gröbner basis {{NonLinearAlgebra_FO0154||FO}} is reduced if the following  two conditions hold: 
(a) The leading coefficient of each polynomial {{NonLinearAlgebra_FO0162||FO}} is 1 . 
(b) For distinct {{NonLinearAlgebra_FO0166||FO}}, no monomial in {{NonLinearAlgebra_FO0060||FO}} is a multiple of in {{NonLinearAlgebra_FO0167||FO}}. 

In what follows we fix an ideal {{NonLinearAlgebra_FO0153||FO}} and a monomial ordering {{NonLinearAlgebra_FO0132||FO}}. 
Theorem 1.16. The ideal I has a unique reduced Gröbner basis for {{NonLinearAlgebra_FO0132||FO}}. 
Proof idea. We refer to {{NonLinearAlgebra_FO0168||FO}}, Theorem 5]. The idea is as follows. We  start with any Gröbner basis {{NonLinearAlgebra_FO0154||FO}} and we turn it into a reduced Gröbner basis  by applying the following steps. First we divide each {{NonLinearAlgebra_FO0162||FO}} by its leading  coefficient to make it monic, so that (a) holds. We then remove all elements {{NonLinearAlgebra_FO0060||FO}}  from {{NonLinearAlgebra_FO0154||FO}} whose initial monomial is not a minimal generator of in {{NonLinearAlgebra_FO0169||FO}}. For any  pair of polynomials with the same initial monomial we delete one of them.  Next we apply the division algorithm [10, §2.3] to any trailing monomial  until no more trailing monomial is divisible by any leading monomial. The  resulting set is the reduced Gröbner basis. 

Let {{NonLinearAlgebra_FO0170||FO}} be the set of all monomials {{NonLinearAlgebra_FO0110||FO}} that are not in the initial ideal  in {{NonLinearAlgebra_FO0169||FO}}. We call these {{NonLinearAlgebra_FO0110||FO}} the standard monomials of {{NonLinearAlgebra_FO0038||FO}} with respect to {{NonLinearAlgebra_FO0132||FO}}. 

Theorem 1.17. The set {{NonLinearAlgebra_FO0171||FO}} of standard monomials is a basis for the  {{NonLinearAlgebra_FO0001||FO}}-vector space {{NonLinearAlgebra_FO0172||FO}}. 

Proof. The image of {{NonLinearAlgebra_FO0171||FO}} in {{NonLinearAlgebra_FO0172||FO}} is linearly independent because every  non-zero polynomial {{NonLinearAlgebra_FO0029||FO}} has at least one monomial, namely in {{NonLinearAlgebra_FO0173||FO}}, that is  not in {{NonLinearAlgebra_FO0174||FO}}. We next prove that {{NonLinearAlgebra_FO0171||FO}} spans {{NonLinearAlgebra_FO0172||FO}}. Suppose not. Then  there exists a monomial {{NonLinearAlgebra_FO0175||FO}} which is not in the {{NonLinearAlgebra_FO0001||FO}}-span of {{NonLinearAlgebra_FO0171||FO}} modulo {{NonLinearAlgebra_FO0038||FO}}.  We may assume that {{NonLinearAlgebra_FO0175||FO}} is minimal with respect to the monomial order {{NonLinearAlgebra_FO0132||FO}}.