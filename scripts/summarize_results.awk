BEGIN {
    OFS = ","
}

NR == 1 {
    next
}

{
    key = $1 FS $2
    runs[key]++
    tree[key] += $8
    tree_squared[key] += $8 * $8
    force[key] += $9
    force_squared[key] += $9 * $9
    total[key] += $10
    total_squared[key] += $10 * $10
}

function sample_sd(sum, sum_squared, count, variance) {
    if (count < 2) {
        return 0
    }

    variance = (sum_squared - (sum * sum / count)) / (count - 1)
    return sqrt(variance > 0 ? variance : 0)
}

END {
    print "language", "variant", "runs", "tree_ms_mean", "tree_ms_std", \
          "force_ms_mean", "force_ms_std", "total_ms_mean", "total_ms_std"

    for (key in runs) {
        split(key, columns, FS)
        count = runs[key]
        print columns[1], columns[2], count, \
              tree[key] / count, sample_sd(tree[key], tree_squared[key], count), \
              force[key] / count, sample_sd(force[key], force_squared[key], count), \
              total[key] / count, sample_sd(total[key], total_squared[key], count)
    }
}
