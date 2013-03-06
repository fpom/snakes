(provide 'abcd-mode)

(define-derived-mode abcd-mode python-mode "ABCD"
  (font-lock-add-keywords
   nil
   `((,(concat "\\<\\(buffer\\|typedef\\|net\\|enum\\|task\\|const\\|symbol\\)\\>")
      1 font-lock-keyword-face t))))
