(defproject metabase/setupranali-driver "1.0.0"
  :description "SetuPranali semantic layer driver for Metabase"
  :url "https://github.com/setupranali/setupranali.github.io"
  :license {:name "Apache-2.0"
            :url "https://www.apache.org/licenses/LICENSE-2.0"}
  
  :min-lein-version "2.5.0"
  
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [clj-http "3.12.3"]
                 [cheshire "5.11.0"]]
  
  :profiles {:provided
             {:dependencies [[metabase-core "1.0.0"]]}}
  
  :plugins [[lein-clean-ns "0.1.0"]]
  
  :source-paths ["src"]
  
  :aot [metabase.driver.setupranali]
  
  :jar-name "setupranali-driver.jar"
  :uberjar-name "setupranali-driver.metabase-driver.jar"
  
  :target-path "target/%s"
  
  :clean-targets ^{:protect false} ["target"])

