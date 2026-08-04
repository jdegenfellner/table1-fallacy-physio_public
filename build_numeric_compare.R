#!/usr/bin/env Rscript
# Modell-Übereinstimmung Mistral vs Qwen2.5 auf den Zählvariablen.
# Scatter (ggplot) + Pearson / Spearman / Lin's CCC. Nur Records, die BEIDE
# als eligible UND baseline_testing=TRUE codieren (dort sind die Zähler sinnvoll).
suppressMessages({library(ggplot2); library(patchwork)})

M <- read.csv("data/extraction_Mistral-Small-3.1-24B.csv", stringsAsFactors = FALSE)
Q <- read.csv("data/extraction_Qwen2.5-32B.csv", stringsAsFactors = FALSE)

keep <- function(d) d[, c("record_id","eligible","baseline_testing",
                          "n_vars_tested","n_vars_significant")]
m <- merge(keep(M), keep(Q), by = "record_id", suffixes = c(".m",".q"))
tl <- function(x) tolower(trimws(as.character(x)))
m <- m[tl(m$eligible.m)=="true" & tl(m$eligible.q)=="true" &
       tl(m$baseline_testing.m)=="true" & tl(m$baseline_testing.q)=="true", ]

ccc <- function(x, y) {
  mx<-mean(x); my<-mean(y)
  vx<-mean((x-mx)^2); vy<-mean((y-my)^2); cv<-mean((x-mx)*(y-my))
  2*cv / (vx + vy + (mx-my)^2)
}

panel <- function(df, field, title) {
  x <- suppressWarnings(as.numeric(df[[paste0(field,".m")]]))
  y <- suppressWarnings(as.numeric(df[[paste0(field,".q")]]))
  ok <- is.finite(x) & is.finite(y); x<-x[ok]; y<-y[ok]; n<-length(x)
  r  <- cor(x,y); rho <- cor(x,y,method="spearman"); cc <- ccc(x,y)
  exact <- mean(x==y)*100; w1 <- mean(abs(x-y)<=1)*100; mad <- mean(abs(x-y))
  lab <- sprintf("n=%d\nPearson r=%.2f\nSpearman rho=%.2f\nLin CCC=%.2f\nexact=%.0f%%  within1=%.0f%%",
                 n, r, rho, cc, exact, w1)
  lim <- max(x,y)
  cat(sprintf("%-20s n=%d  r=%.3f  rho=%.3f  CCC=%.3f  exact=%.0f%%  +-1=%.0f%%  MAD=%.2f\n",
              field, n, r, rho, cc, exact, w1, mad))
  d <- data.frame(x=x, y=y)
  ggplot(d, aes(x, y)) +
    geom_abline(slope=1, intercept=0, linetype="dashed", colour="red") +
    geom_jitter(width=.18, height=.18, alpha=.35, size=1.6, colour="#2c6fbb") +
    annotate("label", x=0, y=lim, label=lab, hjust=0, vjust=1, size=3,
             label.size=0, fill="white", alpha=.7) +
    coord_equal(xlim=c(0,lim), ylim=c(0,lim)) +
    labs(title=title, x="Mistral-Small-24B", y="Qwen2.5-32B") +
    theme_minimal(base_size=12)
}

p1 <- panel(m, "n_vars_tested",      "Baseline-Variablen getestet")
p2 <- panel(m, "n_vars_significant", "davon signifikant (p<0.05)")
combined <- (p1 | p2) +
  plot_annotation(title = "Modell-Übereinstimmung auf Zählvariablen (Mistral vs Qwen2.5)",
                  subtitle = "nur Records, die beide Modelle eligible + baseline_testing=TRUE codieren; Jitter zur Sichtbarkeit")

ggsave("data/model_numeric_agreement_R.png", combined, width=11, height=5.2, dpi=140)
ggsave("data/model_numeric_agreement_R.pdf", combined, width=11, height=5.2)
cat("-> data/model_numeric_agreement_R.png / .pdf\n")
