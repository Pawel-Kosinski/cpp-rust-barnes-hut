using System;
using System.IO;
using System.Globalization;
using System.Runtime.InteropServices;
using System.ComponentModel;

// The job closes with the launcher, including an unexpected console close.
public static class LaptopRuntime {
    [StructLayout(LayoutKind.Sequential)] public struct PowerStatus {
        public byte ACLineStatus, BatteryFlag, BatteryLifePercent, SystemStatusFlag;
        public uint BatteryLifeTime, BatteryFullLifeTime;
    }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimit {
        public long ProcessTime, JobTime;
        public uint Flags;
        public UIntPtr MinWorkingSet, MaxWorkingSet;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)] struct IoCounters {
        public ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes;
    }
    [StructLayout(LayoutKind.Sequential)] struct ExtendedLimit {
        public BasicLimit Basic;
        public IoCounters Io;
        public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
    }
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetSystemPowerStatus(out PowerStatus status);
    [DllImport("kernel32.dll")] static extern uint SetThreadExecutionState(uint flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr security, string name);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job, int info, IntPtr value, uint length);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    public static PowerStatus Power() {
        PowerStatus p;
        if (!GetSystemPowerStatus(out p)) throw new Win32Exception();
        return p;
    }
    public static void Awake(bool enable) {
        if (SetThreadExecutionState(enable ? 0x80000001u : 0x80000000u) == 0)
            throw new Win32Exception();
    }
    public static IntPtr NewJob() {
        IntPtr job = CreateJobObject(IntPtr.Zero, null);
        if (job == IntPtr.Zero) throw new Win32Exception();
        ExtendedLimit limit = new ExtendedLimit();
        limit.Basic.Flags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        int size = Marshal.SizeOf(limit);
        IntPtr ptr = Marshal.AllocHGlobal(size);
        try {
            Marshal.StructureToPtr(limit, ptr, false);
            if (!SetInformationJobObject(job, 9, ptr, (uint)size)) {
                CloseHandle(job);
                throw new Win32Exception();
            }
        } finally { Marshal.FreeHGlobal(ptr); }
        return job;
    }
    public static void Attach(IntPtr job, IntPtr process) {
        if (!AssignProcessToJobObject(job, process)) throw new Win32Exception();
    }
    public static void CloseJob(IntPtr job) { CloseHandle(job); }

    public static double[] Forces(string reference, string actual) {
        var relative = new System.Collections.Generic.List<double>();
        double error2 = 0, norm2 = 0;
        using (var r = new StreamReader(reference))
        using (var a = new StreamReader(actual)) {
            if (r.ReadLine() != "index,acc_x,acc_y" || a.ReadLine() != "index,acc_x,acc_y")
                throw new InvalidDataException("Wrong force CSV header");
            string row;
            int i = 0;
            while ((row = r.ReadLine()) != null) {
                string line = a.ReadLine();
                if (line == null) throw new InvalidDataException("Missing force rows");
                string[] x = row.Split(','), y = line.Split(',');
                if (x.Length != 3 || y.Length != 3 || x[0] != y[0] || int.Parse(x[0]) != i++)
                    throw new InvalidDataException("Force indices differ");
                double rx = Number(x[1]), ry = Number(x[2]);
                double dx = Number(y[1]) - rx, dy = Number(y[2]) - ry;
                double n = rx*rx + ry*ry, e = dx*dx + dy*dy;
                if (n <= 0) throw new InvalidDataException("Zero reference norm");
                norm2 += n; error2 += e;
                relative.Add(Math.Sqrt(e/n));
            }
            if (a.ReadLine() != null || relative.Count == 0)
                throw new InvalidDataException("Unexpected force row count");
        }
        relative.Sort();
        double rank = 0.95 * (relative.Count - 1);
        int lo = (int)Math.Floor(rank), hi = (int)Math.Ceiling(rank);
        double p95 = relative[lo] + (rank - lo) * (relative[hi] - relative[lo]);
        return new double[] {relative.Count, Math.Sqrt(error2/norm2), p95, relative[relative.Count-1]};
    }
    static double Number(string text) {
        double value = double.Parse(text, CultureInfo.InvariantCulture);
        if (double.IsNaN(value) || double.IsInfinity(value))
            throw new InvalidDataException("Non-finite acceleration");
        return value;
    }
}
