

If {{NonLinearAlgebra_FO1372||FO}} for some {{NonLinearAlgebra_FO1373||FO}} then we have {{NonLinearAlgebra_FO1374||FO}}. 
In the following lemma we are claiming that two functions {{NonLinearAlgebra_FO1375||FO}} agree. 
Lemma 7.4. If {{NonLinearAlgebra_FO1376||FO}} then {{NonLinearAlgebra_FO1377||FO}}. 
Proof. By enlarging the field {{NonLinearAlgebra_FO0001||FO}}, we may assume that the value group equals  {{NonLinearAlgebra_FO0005||FO}}. Let {{NonLinearAlgebra_FO1378||FO}} and choose any {{NonLinearAlgebra_FO1373||FO}} with {{NonLinearAlgebra_FO1379||FO}}. A computation shows 
{{NonLinearAlgebra_FO1380||FO}}. 
Hence the two functions agree on every argument {{NonLinearAlgebra_FO1378||FO}}. 
Definition 7.5. Let {{NonLinearAlgebra_FO1381||FO}} be a tropical polynomial, i.e. a function that is  the minimum of finitely many linear functions. A number {{NonLinearAlgebra_FO1382||FO}} is called a  tropical root of {{NonLinearAlgebra_FO0060||FO}} if that minimum is attained at least twice. 

The following facts relate classical root finding and tropical root finding. 
Theorem 7.6. Let {{NonLinearAlgebra_FO1371||FO}} and {{NonLinearAlgebra_FO1383||FO}} its tropicalization. If {{NonLinearAlgebra_FO1373||FO}}  satisfies {{NonLinearAlgebra_FO1384||FO}} then {{NonLinearAlgebra_FO1372||FO}} is a tropical root of {{NonLinearAlgebra_FO0060||FO}}. Conversely, if {{NonLinearAlgebra_FO0001||FO}} is  algebraically closed then every tropical root {{NonLinearAlgebra_FO1334||FO}} of {{NonLinearAlgebra_FO0060||FO}} arises from a zero {{NonLinearAlgebra_FO1360||FO}} of {{NonLinearAlgebra_FO0029||FO}}. 

Proof. Let {{NonLinearAlgebra_FO1385||FO}} and suppose {{NonLinearAlgebra_FO1386||FO}} is zero. Then  {{NonLinearAlgebra_FO1387||FO}} but {{NonLinearAlgebra_FO1388||FO}} for {{NonLinearAlgebra_FO1389||FO}}. Using [37, Lemma 2.1.1],  this implies {{NonLinearAlgebra_FO1390||FO}} for some {{NonLinearAlgebra_FO1391||FO}} and all {{NonLinearAlgebra_FO1392||FO}}.  This means that {{NonLinearAlgebra_FO1372||FO}} is a tropical zero of the {{NonLinearAlgebra_FO1383||FO}}. 

Our proof of the second statement follows that of [37, Proposition 3.1.5].  We assume that {{NonLinearAlgebra_FO1334||FO}} is a tropical root. Since {{NonLinearAlgebra_FO0001||FO}} is algebraically closed, we can  factor {{NonLinearAlgebra_FO1393||FO}}. Since {{NonLinearAlgebra_FO1334||FO}} is a tropical root of {{NonLinearAlgebra_FO1370||FO}}, it is also a  tropical root of one of the tropicalized factors, by Lemma 7.4. Hence there is  an index {{NonLinearAlgebra_FO0123||FO}} such that {{NonLinearAlgebra_FO1394||FO}}. This implies {{NonLinearAlgebra_FO1395||FO}}.  We now simply set {{NonLinearAlgebra_FO1396||FO}} in {{NonLinearAlgebra_FO0001||FO}}. Then {{NonLinearAlgebra_FO1384||FO}} and {{NonLinearAlgebra_FO1372||FO}}. 

Example {{NonLinearAlgebra_FO1397||FO}}. Let {{NonLinearAlgebra_FO0029||FO}} be as in Example 7.3 and {{NonLinearAlgebra_FO1383||FO}} its  tropicalization (7.1). The tropical roots of {{NonLinearAlgebra_FO0060||FO}} are the rational numbers {{NonLinearAlgebra_FO1334||FO}}  such that of {{NonLinearAlgebra_FO1398||FO}} and 5 is attained twice. The solutions  are {{NonLinearAlgebra_FO1399||FO}}. These are the valuations of the three roots of {{NonLinearAlgebra_FO0029||FO}}. 

Fields with valuations provide a systematic way of speaking algebraically  about logarithms. This explains the connection between classical arithmetic  and tropical arithmetic. We shall return to this point in our exploration of  varieties in Subsection 7.3. First, however, let us develop some more purely  tropical machinery, in the familiar setting of matrices and linear algebra.