import styles from "../workspace/WorkspaceFrame.module.css";

export type AuthorityTriadProps = { available: boolean; authorised: boolean; active: boolean; reason?: string };

export function AuthorityTriad({ available, authorised, active, reason }: AuthorityTriadProps) {
  const values = [["AVAILABLE", available], ["AUTHORISED", authorised], ["ACTIVE", active]] as const;
  return <div className={styles.authorityBlock} aria-label="Independent capability authority state">
    <div className={styles.authorityTriad}>{values.map(([label, value]) => {
      const displayValue = label === "AUTHORISED" && value ? "READ-ONLY" : value ? "YES" : "NO";
      return <div key={label} className={value ? styles.authorityOn : styles.authorityOff} data-authority-state={`${label}:${value ? "YES" : "NO"}`}><span>{label}</span><strong>{displayValue}</strong></div>;
    })}</div>
    <p className={styles.authorityReason}>{reason ?? "Backend fixture capability · authority effect NONE"}</p>
  </div>;
}
