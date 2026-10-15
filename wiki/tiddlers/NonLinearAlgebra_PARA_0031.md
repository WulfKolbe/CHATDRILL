
corresponds to divisibility of monomials. To be precise, we have {{NonLinearAlgebra_FO0108||FO}} in  {{NonLinearAlgebra_FO0107||FO}} if and only if the monomial {{NonLinearAlgebra_FO0109||FO}} divides the monomial {{NonLinearAlgebra_FO0110||FO}}. 

Theorem 1.8 (Dickson's Lemma). Any infinite subset of {{NonLinearAlgebra_FO0107||FO}} contains a  pair {{NonLinearAlgebra_FO0111||FO}} that satisfies {{NonLinearAlgebra_FO0108||FO}}. 

Proof. We proceed by induction on {{NonLinearAlgebra_FO0015||FO}}. The statement is trivial for {{NonLinearAlgebra_FO0102||FO}}.  Any subset of cardinality at least two in {{NonLinearAlgebra_FO0112||FO}} contains a comparable pair.  Suppose now that Dickson's Lemma has been proved for {{NonLinearAlgebra_FO0113||FO}}, and consider  an infinite subset {{NonLinearAlgebra_FO0114||FO}} of {{NonLinearAlgebra_FO0107||FO}}. For each {{NonLinearAlgebra_FO0115||FO}} let {{NonLinearAlgebra_FO0116||FO}} denote the set of all  vectors {{NonLinearAlgebra_FO0117||FO}} such that {{NonLinearAlgebra_FO0118||FO}}. If some {{NonLinearAlgebra_FO0116||FO}} is infinite then we are  done by the induction hypothesis. Hence each {{NonLinearAlgebra_FO0116||FO}} is a finite subset of {{NonLinearAlgebra_FO0119||FO}},  and we have {{NonLinearAlgebra_FO0120||FO}} for infinitely many {{NonLinearAlgebra_FO0121||FO}}. 

The infinite subset {{NonLinearAlgebra_FO0122||FO}} of {{NonLinearAlgebra_FO0119||FO}} satisfies the assertion. This means  that its subset of minimal elements with respect to the coordinatewise order  is finite. Hence there exists an index {{NonLinearAlgebra_FO0123||FO}} such that all minimal elements are  contained in the finite set {{NonLinearAlgebra_FO0124||FO}}. Pick any element {{NonLinearAlgebra_FO0125||FO}} for {{NonLinearAlgebra_FO0126||FO}}.  Since {{NonLinearAlgebra_FO0127||FO}} is not minimal in {{NonLinearAlgebra_FO0122||FO}}, there exists an index {{NonLinearAlgebra_FO0121||FO}} with {{NonLinearAlgebra_FO0128||FO}}  and an element {{NonLinearAlgebra_FO0129||FO}} with {{NonLinearAlgebra_FO0108||FO}}. Then we have {{NonLinearAlgebra_FO0130||FO}} in {{NonLinearAlgebra_FO0114||FO}}. 

Corollary 1.9. For any nonempty set {{NonLinearAlgebra_FO0131||FO}}, its subset of coordinatewise  minimal elements is finite and nonempty. 

Proof. The fact that it is nonempty follows by induction on {{NonLinearAlgebra_FO0015||FO}}. The set is  finite by Dickson's Lemma. 

Definition 1.10. Consider a total ordering {{NonLinearAlgebra_FO0132||FO}} of the set {{NonLinearAlgebra_FO0107||FO}}. We write {{NonLinearAlgebra_FO0133||FO}}  if {{NonLinearAlgebra_FO0134||FO}} or {{NonLinearAlgebra_FO0135||FO}}. The ordering {{NonLinearAlgebra_FO0132||FO}} is a monomial order if, for all {{NonLinearAlgebra_FO0136||FO}}, 
- {{NonLinearAlgebra_FO0137||FO}}; 
- {{NonLinearAlgebra_FO0133||FO}} implies {{NonLinearAlgebra_FO0138||FO}}. 

This gives a total order on monomials in {{NonLinearAlgebra_FO0021||FO}}. Three standard examples are: 
- the lexicographic ordering: we set {{NonLinearAlgebra_FO0139||FO}} if the leftmost non-zero  entry of {{NonLinearAlgebra_FO0140||FO}} is positive. 
- the degree lexicographic order: we set {{NonLinearAlgebra_FO0141||FO}} if either {{NonLinearAlgebra_FO0142||FO}},  or {{NonLinearAlgebra_FO0143||FO}} and the leftmost non-zero entry of {{NonLinearAlgebra_FO0144||FO}} is positive. 
- the degree reverse lexicographic order: we set {{NonLinearAlgebra_FO0145||FO}} if either  {{NonLinearAlgebra_FO0142||FO}}, or {{NonLinearAlgebra_FO0143||FO}} and the rightmost non-zero entry of {{NonLinearAlgebra_FO0144||FO}} is  negative. 

All three orders satisfy {{NonLinearAlgebra_FO0146||FO}}, but they differ on monomi als of higher degree. We recommend that the reader list the 10 quadratic  monomials for {{NonLinearAlgebra_FO0147||FO}} in each of the three orderings above.