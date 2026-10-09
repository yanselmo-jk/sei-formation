"""The two linear-algebra routines this package needs, in stdlib Python.

There is no numpy and there will not be: the package is air-gapped, `pip`-less and stdlib-only by
requirement. Both routines here are small, exact for the sizes we use them at (3x3 and 4x4), and
have their limits written down.

🔒 ONE COPY. `guards.coplanarity` (best-fit plane, symmetric 3x3) and `conformers.rmsd`
(quaternion RMSD, symmetric 4x4) both need a symmetric eigensolver. Two copies of an eigensolver
is the "same truth in two places" shape that has cost this project six rounds, so the general
routine lives here and both import it.
"""

import math


def jacobi_eigen(matrix, max_sweeps=64, tol=1e-20):
    """Eigenvalues and eigenvectors of a REAL SYMMETRIC matrix, by cyclic Jacobi rotation.

    Returns `(values, vectors)` where `vectors[i][k]` is component `i` of eigenvector `k`
    (eigenvectors are COLUMNS). Order is unspecified -- callers select by value.

    🔴 Valid only for symmetric input. The caller is responsible for that; we do not symmetrise
       silently, because a caller passing a non-symmetric matrix has a bug and averaging it away
       would hide it. `assert_symmetric` is provided for callers that want the check.
    🟢 Cyclic Jacobi is unconditionally convergent for symmetric matrices and is exact to machine
       precision at these sizes. It handles DEGENERATE eigenvalues correctly, which matters:
       `guards.coplanarity` calls it on the covariance matrix of a set of atoms, and a LINEAR
       arrangement of >= 4 heavy atoms produces two equal (zero) eigenvalues. Jacobi returns an
       arbitrary but ORTHONORMAL pair spanning that subspace rather than failing.
    """
    n = len(matrix)
    a = [list(row) for row in matrix]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_sweeps):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-18:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p] = c * vkp - s * vkq
                    v[k][q] = s * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


def assert_symmetric(matrix, tol=1e-9):
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(matrix[i][j] - matrix[j][i]) > tol:
                raise ValueError("matrix is not symmetric at (%d,%d): %r vs %r"
                                 % (i, j, matrix[i][j], matrix[j][i]))
    return matrix


def smallest_eigenvector(matrix):
    """Unit eigenvector belonging to the smallest eigenvalue. The best-fit-plane normal."""
    vals, vecs = jacobi_eigen(matrix)
    k = min(range(len(vals)), key=lambda i: vals[i])
    vec = [vecs[i][k] for i in range(len(vals))]
    norm = math.sqrt(sum(c * c for c in vec)) or 1.0
    return [c / norm for c in vec], vals[k]


def largest_eigenvalue(matrix):
    return max(jacobi_eigen(matrix)[0])
