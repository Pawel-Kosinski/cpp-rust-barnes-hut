struct Node
{
    float boundsX{0.0f};
    float boundsY{0.0f};
    float halfSize{0.0f};
    float mass{0.0f};
    float centerX{0.0f};
    float centerY{0.0f};
    int particleIndex{-1}; // Index of the particle in the original vector, -1 if it's an internal node
    int children[4]{-1, -1, -1, -1}; // Indices of the child nodes in the quadtree vector, -1 if no child
    int next{-1};
};