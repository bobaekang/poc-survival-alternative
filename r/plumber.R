library(jsonlite)
library(survival)

DATA_URL <- "https://" # JSON data endpoint
MOCK <- TRUE

fetch_data <- function(url) {
  content(fromJSON(url), as = "parsed")
}

fetch_fake_data <- function() {
  data <- read_json("../data.json", simplifyVector = TRUE)
  colnames(data) <- tolower(colnames(data))
  data$time <- data$stime / 365
  data$status <- data$scens == 1
  data[data$time >= 0, c("time", "status", "sex", "race")]
}

get_strata_vector <- function(strata) {
  unlist(lapply(seq_along(strata), function(i) {
    rep(trimws(names(strata)[i]), strata[i])
  }))  
}

df2list <- function(df) {
  lapply(seq_len(nrow(df)), function(i) as.list(lapply(df, "[", i)))
}

get_risktable <- function(x, yearmax) {
  fill_na <- function(x) {
    c(0, x[!is.na(x)])[cumsum(!is.na(x)) + 1]
  }

  vec <- c(x$nrisk[1], sapply(split(x$nrisk, ceiling(x$time)), min))
  df <- merge(
    data.frame(year = fill_na(as.numeric(names(vec))), n = vec),
    data.frame(year = 0:yearmax),
    all = TRUE
  )
  df$n <- fill_na(df$n)
  df2list(df[c('n', 'year')])
}

get_survival_data <- function(data, factor) {
  trt <- if (factor == "") 1 else factor
  formula <- as.formula(paste0("Surv(time, status) ~ ", trt))
  fit <- survfit(formula, data = data)

  survdf = data.frame(
    nrisk = fit$n.risk,
    prob = fit$surv,
    time = fit$time
  )

  if (factor == "") {
    survival <- df2list(survdf['prob', 'time'])
    pval <- NA
    risktable <- get_risktable(survdf, max(survdf$time))
  } else {
    survdf$strata <- get_strata_vector(fit$strata)
    survival <- lapply(split(survdf, survdf$strata), function(x) {
      df2list(x[c('prob', 'time')])
    })
    
    sdiff <- survdiff(eval(fit$call$formula), data = data)
    pval <- stats::pchisq(sdiff$chisq, length(sdiff$n) - 1, lower.tail = FALSE)

    risktable <- lapply(split(survdf, survdf$strata), function(x) {
      get_risktable(x, max(survdf$time))
    })
  }
  
  list(pval = pval, risktable = risktable, survival = survival)
}

#' Get survival analysis results
#' @get /
#' @serializer unboxedJSON
function(factor = "") {
  data <- if (MOCK) fetch_fake_data() else fetch_data(DATA_URL)
  get_survival_data(data, factor)
}
