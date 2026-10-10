// A separately compiled driver demonstrates the manifest contract without
// claiming a new solver implementation: the other translation unit is V1.
int reference_entry(int argc, char** argv);
int main(int argc, char** argv) {
    return reference_entry(argc, argv);
}
