/*!
 * jQuery simulator plugin
 * version 2.4.2
 * Copyright 2014, IBISC University Evry Val d'Essonne, dev by Jean-Baptiste Munieres
 *
 */

//TOTEST :S => Success, B => Bug, N => Non tested, R => new version retry all test
/*

1er jet de test => trace only:

    Faire des successions d'etat : S
    Revenir dans la trace : S
    Ecraser la trace pour une nouvelle : S => probleme avec le off(click **)
    Revenir Init : S
    Revenir a la Fin : S
    Repartir de la fin pour continuer la trace : S
    Lancer le player : S
    Stoper le player en cours : S
    Stop et Play succesivement : S
    Accelerer la vitesse : S
    Baisser la vitesse : S
    Faire en play milieu de la trace : S
    Test l'aide : N
    Test Stop simulation : R
    Test Reset simulation : S
    
2eme jeu de test => graph & trace:
    
    A faire dans le graph :

        Faire des successions d'etat : S
        Revenir dans la trace : S
        Ecraser la trace pour une nouvelle : S
        Lancer le player : S
        Stoper le player en cours : S
        Stop et Play succesivement : S
        Accelerer la vitesse : S
        Baisser la vitesse : S
        Faire en play milieu de la trace : S
        Test Reset simulation : S
        
        Decocher la case pour afficher toutes les variables : S
        Decocher les variables une par une : S
        Cocher la case pour afficher toutes les variables : S
        Cocher les variables une par une : S
        
        Afficher les tooltips depuis l'axe des x : S
        Afficher un tooltip depuis un point : S
        
    A faire dans la trace avec nouvelle version :
        Tester tout dans 1er jeu
        
        Changer le debut de l'interval : S
        Avec un debut d'interval modifier :
            Faire des succesions d'etat : S
            Ecraser la trace pour une nouvelle : S
            Changer la fin de trace : S
            Impossibilite d'avoir fin < debut : S
            Revenir direct a la fin depuis le graphe : S
            Choisir le debut sur la trace & fin sur le graph : S
            
        Groups
            Decocher la case qui active toutes les transitions : S
            Decocher les transitions un par un : S
            Cocher la case qui active toutes les transitions : S
            Cocher les transitions une par une : S
            
            Refaire ce qu'il y a plus haut avec en plus :
                Changer l'interval : S S S S
*/

(function($) {
    
    //Plugin for function who need object
    //Ne pas rebind plusieur fois sur le meme objet sous peine de gros lag
    jQuery.fn.simisc = function(option, callback){
        
        /**
         *  @description Add attribute and click handler for get_state
         *  @param {Integer} key  The state number to get
         *  @param {Integer} instance_key The key for get the data (only for next version (3.0))
         */
        $.fn.get_attr_link = function(key, instance_key) {
            console.log("get_attr_link")
            $(this).attr({"data-num": key})
            $(this).on("click",get_trace)
        }
        
        /**
         *  @description Add attributes and click handler for set_state
         *  @param {Integer} value  Dictionnary for set a new state : { action : String, state : Integer, mode : Integer  }
         *  @param {Integer} instance_key The key for get the data (only for next version (3.0))
         */
        $.fn.set_attr_link = function(value, instance_key){
            console.log("set_attr_link")
            $(this).attr({"data-action": value.action , "data-state" : value.state, "data-mode" : value.mode, "data-groups" : value.groups})
            $(this).on("click",set_trace)
        }
        
        /**
         * @description @see $.fn.set_attr_link
         */
        function set_trace(object, instance_key) {
            $.simisc.set_trace(this, instance_key );
        }
        
        /**
         * @description @see $.fn.get_attr_link
         */
        function get_trace(object, instance_key) {
            $.simisc.get_trace(this, instance_key );
        }
        
        //Remove all handler on object (optimise for just delete the handler of click)
        $(this).off()
            
        //Reset the attributes for object
        $(this).removeAttr("data-num data-action data-mode data-state")
        
        return $(this)
    }
    
    //Plugin principal
    jQuery.simisc = function (options, callback) {
    
        // if the first argument is a function then assume the options aren't being passed
        if (jQuery.isFunction(options)) {
            callback = options;
            options = {};
        }
        else{
        
            // Merge passed settings with default values
            $.simisc.instance.push($.extend(true, {}, $.simisc.defaults, options));
        
            //For version 3.0 with multiple simulator in same page
            var instance_key = $.simisc.instance.length-1,
            settings = $.extend(true, {}, $.simisc.defaults, options),
            //Contains all the history
            _history,
            _data,
            //Contains the current state num for user
            _clk_end,
            //Contains the begin state
            _clk_begin,
            //Current trace
            _trace,
            //Current modes
            _modes,
            //Current variables
            _variables,
            //Current groups to see
            _groups,
            //True if we look into the history
            _isHistory,
            //Contain all variables for graph
            _graph = {},
            //variables for player
            _record = {
                "speed":1,
                "max_speed":16,
                "play": false
            },
            //Function can be call by simulator
            update = {
                settext : function (action) {
                    $(action.select).text(action.text);
                },
                sethtml : function (action) {
                    $(action.select).html(action.html);
                },
                clear : function (action) {
                    $(action.select).html("");
                },
                setlist : function (action) {
                    ul = $(action.select);
                    ul.html("");
                    $.each(action.items, function (num, item) {
                        ul.append("<li>" + item + "</li>");
                    });
                },
                dropclass : function (action) {
                    $(action.select).removeClass(action.class);
                },
                addclass : function (action) {
                    $(action.select).addClass(action.class);
                }
            };
            //Init all the simulator
            init();
        }
        
        /**
         *  @description Function for create/add the player to the view
         */
        function init_player() {
            console.log("init player")
            div = document.createElement("div")
            
            div_gauche = document.createElement("div")
            div_bouton = document.createElement("div")
            
            span = document.createElement("span")
            input = document.createElement("input")
            
            div_droite = document.createElement("div")
            span = document.createElement("span")
            
            $(div).attr({
                "class": "input-group col-md-12",
                "id": "frames"
            });
            
            $(div_bouton).attr({
                "class": "btn-group"
            })
            
            //Left part of player
            span = document.createElement("span")
            $(span).addClass("glyphicon glyphicon-play")
            
            bouton_play = document.createElement("div")
            $(bouton_play).attr({
                    "id": "simisc_play",
                    "type": "button",
                    "class": "btn btn-default",
                })
                .tooltip({
                    title: "Launch the player",
                    trigger: "hover",
                    placement: "top",
                    delay: { show: 500, hide: 100 }
                })
                .append(span)
                .click(function(){
                    play(this)
                })
                
            
            span = document.createElement("span")
            $(span).addClass("glyphicon glyphicon-stop")
            
            bouton_stop = document.createElement("div")
            $(bouton_stop).attr({
                    "id": "simisc_stop",
                    "type": "button",
                    "class": "btn btn-default",
                    "style": "display:none;"
                })
                .tooltip({
                    title: "Stop the player",
                    trigger: "hover",
                    placement: "top",
                    delay: { show: 500, hide: 100 }
                })
                .append(span)
                .click(function(){
                    stop(this)
                })
            
            $(div_gauche).attr({
                "class": "input-group-btn",
                "id": "simisc_left_player"
                })
                .append([bouton_play, bouton_stop])
            
            //Input in middle
            $(input).attr({
                "value": 10,
                "type": "text",
                "class": "form-control"
            });
            
            
            //Right part of player
            span = document.createElement("span")
            $(span).addClass("glyphicon glyphicon-minus-sign")
            
            bouton_moins = document.createElement("div")
            $(bouton_moins).attr({
                "id": "simisc_down",
                "type": "button",
                "class": "btn btn-default"
                })
                .tooltip({
                    title: "Click for down the speed per tick",
                    trigger: "hover",
                    placement: "top",
                    delay: { show: 500, hide: 100 }
                })
                .append(span)
                .click(function(){
                    down_speed()
                })
                
            
            span = document.createElement("span")
            $(span).addClass("glyphicon glyphicon-plus-sign")
            
            bouton_plus = document.createElement("div")
            $(bouton_plus).attr({
                "id": "simisc_up",
                "type": "button",
                "class": "btn btn-default"
                })
                .tooltip({
                    title: "Click for up the speed per tick",
                    trigger: "hover",
                    placement: "top",
                    delay: { show: 500, hide: 100 }
                })
                .append(span)
                .click(function(){
                    up_speed()
                })
            
            $(div_droite).attr({
                "class": "input-group-btn"
                })
                .append([bouton_moins, bouton_plus])
            
            span = document.createElement("span")
            $(span).attr({
                "class": "input-group-addon",
                "style": "width:56px;text-align:left"
            })
            
            
            $(div).append([div_gauche, input, span, div_droite])
            
            $(settings.player.id).append(div);
            set_speed();
            
            create_modal(settings.player.modal)
                        
            $(settings.player.modal.id + " .btn-primary").on("click",function(){
                    play(this, true)
            })
        }
        
        /**
         *  @description Launch the player
         */
        function play(object, force){
            console.log("play");
            
            //If we are in history, we ask the conform to delete trace
            if(force != true && _clk_end < _history.trace.length-1){
                $(settings.player.modal.id).modal();
            }
            else{
                _record.play = true;
                
                _record.begin_frame = _clk_end
                _record.end_frame = _clk_end + parseInt($("#frames input").val(),10);
                
                //Hide all and show stop
                $(settings.player.id + " #simisc_play").hide().appendTo("#simisc_left_player");
                $(settings.player.id + " #simisc_stop").show();
                
                //Disabled up & down
                $(settings.player.id + " #simisc_up").attr("disabled","");
                $(settings.player.id + " #simisc_down").attr("disabled","");
                if (_clk_end < _history.trace.length-1) {
                    cut_trace(0,_clk_end+1)
                }
                _isHistory = false;
                
                $.periodic({period: _record.speed * 1000, decay:1, max_period: _record.speed * 1000}, function() {
                    this.cur_period = _record.speed * 1000;
                    this.max_period = _record.speed * 1000;
        
                    //If there is no more modes to run we stop the player
                    if (!_history.modes[_clk_end] || _history.modes[_clk_end].length == 0){
                        stop(object);
                        this.cancel();
                    }
                    else{
                        _record.begin_frame++;
            
                        rdn = Math.floor((Math.random()*_history.modes[_clk_end].length));
                        
                        //Create the fake object a for force an set_trace with rdn mode
                        a = document.createElement("a");
                        
                        $(a).simisc().set_attr_link(_history.modes[_clk_end][rdn], instance_key);
                        $(a).html($(a).attr("data-action"))
                        
                        //If stop is push we stop
                        if (_record.play == false || _record.begin_frame == _record.end_frame){
                            stop(object);
                            this.cancel();
                        }
                        
                        //GO to the new state
                        $.simisc.set_trace($(a));                        
                    }
                });
            }
        }

        /**
         *  @description Stop the player
         */
        function stop(object){
            console.log("stop");
            _record.play = false;
            //Hide all and show stop
            $(settings.player.id + " #simisc_play").show();
            $(settings.player.id + " #simisc_stop").hide().appendTo("#simisc_left_player");
            
            //Disabled up & down
            $(settings.player.id + " #simisc_up").removeAttr("disabled");
            $(settings.player.id + " #simisc_down").removeAttr("disabled");
        }
        
        /**
         *  @description Down the speed between each ticks
         */
        function down_speed(){
            console.log("down speed");
            _record.speed = Math.min(_record.max_speed,_record.speed * 2);
            set_speed();
        }
        
        /**
         *  @description Up the speed between each ticks
         */
        function up_speed(){
            console.log("up_speed");
            _record.speed = Math.max(1/_record.max_speed,_record.speed / 2);
            set_speed();
        }

        //TODO : afficher le speed avec une fraction => moins rapide = 1/16 plus rapide 16
        /**
         *  @description Set the speed in variable and in view
         */
        function set_speed(){
            console.log("set_speed")
            
            text = "16"
            
            switch (_record.speed) {
                case 8 : ;
                case 4 : ;
                case 2 : ;
                case 1 : text = _record.speed; break;
                case 0.5 : text = "<sup>1</sup>/<sub>2</sub>"; break;
                case 0.25 : text = "<sup>1</sup>/<sub>4</sub>"; break;
                case 0.125 : text = "<sup>1</sup>/<sub>8</sub>"; break;
                case 0.0625 : text = "<sup>1</sup>/<sub>16</sub>"; break;
            }
            
            $("#frames .input-group-addon").html("&times;" + text)
        }
      
        /**
         *  @description Init the trace, by creating the table, who will contain all history
         */
        function init_trace(){
            table = document.createElement("table")
            thead = document.createElement("thead")
            tbody = document.createElement("tbody")
            tr = document.createElement("tr")
            
            $(table).addClass("table table-hover")
            
            th = document.createElement("th")
            $(th).addClass("col-md-1")
                .html("#")
            $(tr).append(th)
            
            th = document.createElement("th")
            $(th).html("Action")
            $(tr).append(th)
            
            th = document.createElement("th")
            $(th).html("Modes")
            $(tr).append(th)
            
            th = document.createElement("th")
            $(th).html("States")
            $(tr).append(th)
            
            if (settings.graph.groups === true) {
                th = document.createElement("th")
                $(th).html("Groups")
                $(tr).append(th)
            }
            
            
            th = document.createElement("th")
            $(th).addClass("col-md-1")
            $(tr).append(th)
            
            if (settings.graph.interval) {
                th = document.createElement("th")
                $(th).addClass("col-md-1")
                $(tr).append(th)
            }
            
            $(tbody).attr("id","simisc_trace")
            
            $(thead).append(tr)
            $(table).append(thead,tbody)
            
            $(settings.trace.id).append(table)
        }
        
        /**
         *  @description Init all variables
         */
        function init_vars(){
            //Load initial state
            _trace = {
                "action": settings.init.action,
                "mode": settings.init.mode,
                "state": settings.init.state,
            }
            _isHistory = false
            _history = {
                "trace": new Array(_trace),
                "modes": new Array(),
                "variables": new Array(),
                "data": new Array()
            }
            _clk_end = 0;
            _clk_begin = 0;
            _variables = {}
        }
        
        /**
         *  @description Init the helper
         *  @param {Dict} helper Contain a dictionnary with all content for help, cf bootstrap / popover for the dictionary syntaxe
         */
        function init_help(helper){
            console.log("init_help")
            //console.log(helper)
            $.each(helper, function(key, value){
                value = $.extend({
                    "placement":"auto",
                    "trigger": "manual"
            
                }, value);
                //console.log(value);
                $(key).popover(value);
                $(key).addClass("help-ui");
                $(key).click(function(event){
                    event.stopImmediatePropagation();
                });
            });
        }
        
        /**
         *  @description Init the graph using D3.js
         *  @param {Dict<String:Integer>} variables Contains a dictionnary with couples name value
         */
        function init_graph(variables,groups) {
            console.log("init graph variables")
            _graph.variables = new Array();
            _graph.groups = new Array();
        
            if(!settings.graph.color)
                settings.graph.color = {}
        
            for(key in groups){
                _graph.groups.push(groups[key])
            }
            
            _groups = _graph.groups
            _groups.push("others")
        
            for(key in variables){
                _graph.variables.push(key)
        
                if(!(key in settings.graph.color))
                    settings.graph.color[key] = "pink"
            }
            
            console.log(_graph.groups)
            console.log("init graph")
            
            $.extend(true, variables, {"transition": settings.init.action, "groups": settings.init.groups})
            
            set_history(_clk_end, {"variables":variables})
            
            var max = [0]
            _data = _history.variables
            
            if (_clk_end == _clk_begin) {
                _data.push(_data[0])
            }
            
            //Init the marge & width of graph
            _graph.margin = {top: 30, right: 20, bottom: 200, left: 40},
            _graph.width = $(settings.graph.id).width() - _graph.margin.left - _graph.margin.right,
            _graph.height = 150 - _graph.margin.top + _graph.margin.bottom;
        
            
            _graph.x = d3.scale.linear().range([0, _graph.width]);
        
            _graph.y = d3.scale.linear().range([_graph.height, 0]);
            
            //We create the x axis
            _graph.xAxis = d3.svg.axis().scale(_graph.x)
                .orient("bottom")
                .tickFormat(function(d,i){
                    //We take only the integer part & return the transition cross
                    if(parseFloat(d,10) == parseInt(d,10)){
                        if (_clk_end == _clk_begin && d == 1) {
                            return ""
                        }
                        return _data[d]['transition']
                    }
                    return ''
                });
        
            //We create the y axis
            _graph.yAxis = d3.svg.axis().scale(_graph.y)
                .orient("left").ticks(5);
        
            //Reset the zone if user write element on it (dumbproof)
            $(settings.graph.id).html("")
        
            //Add the table with variable
            init_control_command()
                
            //Add the graph
            _graph.svg = d3.select(settings.graph.id)
                .append("svg")
                .attr("width", _graph.width + _graph.margin.left + _graph.margin.right)
                .attr("height", _graph.height + _graph.margin.top + _graph.margin.bottom)
                .append("g")
                .attr("transform", "translate(" + _graph.margin.left + "," + _graph.margin.top + ")");
        
            //Contains the lines for each variable
            _graph.line = []
        
            _graph.x.domain([0,1]);
            
            //Create the x axis in view
            _graph.svg.append("g")
                .attr("class", "x axis")
                .attr("transform", "translate(0," + _graph.height + ")")
                .call(_graph.xAxis);
            
            //Create the y axis in view
            _graph.svg.append("g")
                .attr("class", "y axis")
                .call(_graph.yAxis);
        
            _graph.variables.forEach(function(v){
                _graph.line[v] = d3.svg.line()
                    .interpolate("step-after")
                    .x(function(d,i) {
                        return _graph.x(i);
                    })
                    .y(function(d) {
                        return _graph.y(d[v]);
                    })
        
                max.push(d3.max(_data, function(d) { return d[v]; }));
        
                _graph.svg.append("path")
                    .attr("class", "line line-" + v)
                    .attr("var",v)
                    .attr("d", _graph.line[v](_data))
                    .attr("style","cursor:pointer;")
                    .style("stroke", settings.graph.color[v])
        
            });
            //TODO : quand on clique trop vite dans le tableau : les points apparaissent
        
            _graph.y.domain([0, d3.max(max, function(d) { return d; })])
        }
        
        //TOREDO parce que D3 pour du tableau c'est moyen
        /**
         *  @description Init the control command for variable, with the tab pannel for (un)select variables and change the interval of visualisation
         */
        function init_control_command() {
            console.log("init_control_command")
            //We add the table on the zone for graph (it's better when call first)
            _graph.table = d3.select(settings.graph.control_panel)
                .append("table")
                .attr("class","table table-bordered table_var")
        
            //ADD variable
            _graph.thead = _graph.table.append("thead")
            
            _graph.tbody = _graph.table.append("tbody")
            
            // append the header row
            _graph.thead.append("tr")
                .selectAll("th")
                //Tab for thead
                .data(["vars","<input class='check_all_vars' type='checkbox' checked />"])
                .enter()
                .append("th")
                .attr("class","active")
                .html(function(column) {
                    console.log(column)
                    return column;
            });
        
            var tab_var = []
         
            _graph.variables.forEach(function(d){
                tab_var.push([d, "<input class='check_var' type='checkbox' checked var='" + d + "' />"])
            })
            
            // create a row for each object in the data
            _graph.rows = _graph.tbody.selectAll("tr")
                .data(tab_var)
                .enter()
                .append("tr");
        
            // create a cell in each row for each column
            _graph.cells = _graph.rows.selectAll("td")
                .data(function(row) {
                    return ([0,1]).map(function(column) {
                        console.log(column)
                        return {column: column, value: row[column]};
                    });
                })
                .enter()
                .append("td")
                .attr("style", "font-family: Courier")
                .html(function(d) { return d.value; });
                
            if (settings.graph.groups) {
                _graph.thead_groups = _graph.table.append("thead")
            
                _graph.tbody_groups = _graph.table.append("tbody")
                
                // append the header row
                _graph.thead_groups.append("tr")
                    .selectAll("th")
                    //Tab for thead
                    .data(["groups","<input class='check_all_groups' type='checkbox' checked />"])
                    .enter()
                    .append("th")
                    .attr("class","active")
                    .html(function(column) {
                        return column;
                });
                    
                var tab_groups = []
         
                _graph.groups.forEach(function(d){
                    tab_groups.push([d, "<input class='check_group' type='checkbox' checked group='" + d + "' />"])
                });
                
                // create a row for each object in the data
                _graph.rows_groups = _graph.tbody_groups.selectAll("tr")
                    .data(tab_groups)
                    .enter()
                    .append("tr");
            
                // create a cell in each row for each column
                _graph.cells_groups = _graph.rows_groups.selectAll("td")
                    .data(function(row) {
                        return ([0,1]).map(function(column) {
                            return {column: column, value: row[column]};
                        });
                    })
                    .enter()
                    .append("td")
                    .attr("style", "font-family: Courier")
                    .html(function(d) { return d.value; });
                    
                 $('.check_all_groups').click(function(){
                    if ($(this).is(":checked")) {
                        $('.check_group').prop("checked", true);
                        _groups = _graph.groups
                        toggle_path("",true)
                    }
                    else{
                        $('.check_group').prop("checked", false);
                        _groups = Array()
                        fade_path("",true)
                    }
                })
                 
                $('.check_group').click(function(){
                    var _group = $(this).attr("group")
                    if ($(this).is(":checked")) {
                        if ( $(".check_group:checked").length == $(".check_group").length){
                            $('.check_all_groups').prop("checked", true);
                        }
                        _groups.push(_group)
                        toggle_path("",true)
                        
                    }
                    else{
                        $('.check_all_groups').prop("checked", false);
                        _groups = Array()
                        
                        $(".check_group:checked").each(function(){
                            _groups.push($(this).attr("group"))
                        })
                        
                        if ( $(".check_group:checked").length == 0){
                            fade_path("",true)
                        }
                        else{
                            print_option();
                        }                        
                    }
                    
                })
            }
            
            if (settings.graph.interval) {
                _graph.thead_interval = _graph.table.append("thead")
                _graph.tbody_interval = _graph.table.append("tbody")
                
                _graph.thead_interval.append("tr")
                    .selectAll("th")
                    .data(["Interval","<a id='reset_interval'> Reset</a>"])
                    .enter()
                    .append("th")
                    .attr("class","active")
                    .html(function(column) {
                        console.log(column)
                        return column;
                    })
                    
                _graph.rows_interval = _graph.tbody_interval.selectAll("tr")
                    .data([["Begin","<input id='begin_interval' class='form-control  col-md-3' type='number' value='0' />"],["End","<input id='end_interval' class='form-control col-md-3' type='number' value='0' />"]])
                    .enter()
                    .append("tr");
                    
                _graph.cells_interval = _graph.rows_interval.selectAll("td")
                .data(function(row) {
                    return ([0,1]).map(function(column) {
                        console.log(column)
                        return {column: column, value: row[column]};
                    });
                })
                .enter()
                .append("td")
                .attr("style", "font-family: Courier")
                .html(function(d) { return d.value; });
                
                $("#reset_interval").on("click", function(){
                    change_begin(0)
                }).get_attr_link(0, instance_key)
                
               
                $("#begin_interval").on("change",function(){
                    val = parseInt($(this).val(),10)
                    if (val != _clk_begin) {
                        if (val > _clk_end) {
                            val = _clk_end
                        }
                        else if(val < 0){
                            val = 0
                        }
                        change_begin(val)
                    }
                })
                
                $("#end_interval").get_attr_link(0, instance_key)
                
                $("#end_interval").on("change",function(){
                    val = parseInt($(this).val(),10)
                    if(val != _clk_end){
                        if (val < _clk_begin) {
                            val = _clk_begin
                        }
                        else if (val >= _history.trace.length) {
                            val = _history.trace.length-1
                        }
                        $(this).attr("data-num",val)
                        $.simisc.get_trace($(this));                   
                    }
                })
                
            }
            
             
            //Check all is the checkbox on thead, you can affich/desable all variables
            $('.check_all_vars').click(function(){
                if ($(this).is(":checked")) {
                    $('.check_var').prop("checked", true);
                    toggle_path("",true)
                }
                else{
                    $('.check_var').prop("checked", false);
                    fade_path("",true)
                }
            })
            
           
                
            //For fade or toggle variable one per one
            $('.check_var').click(function(){
                var _var = $(this).attr("var")
                if ($(this).is(":checked")) {
                    if ( $(".check_var:checked").length == $(".check_var").length){
                        $('.check_all_vars').prop("checked", true);
                    }
                    toggle_path($(this).attr("var"),false)
                }
                else{
                    $('.check_all_vars').prop("checked", false);
                    fade_path($(this).attr("var"),false)
                }
            })
        }
      
        /**
         *  @description Change the begin in graph visualisation
         */
        function change_begin(num) {
            _clk_begin = num
            print_option()
            update_command_center()
        }
        
        /**
         * @description Create a Bootstrap modal with custom id, title, text & button primary text
         * @param {Dict} modal Dict with id, title, text, button_text for modal
         */
        function create_modal(modal){            
            $("body").append('<div class="modal fade" id="' + modal.id.substring(1) + '"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times</button><h4 class="modal-title">' + modal.title + '</h4></div><div class="modal-body"><p>' + modal.text + '</p></div><div class="modal-footer"><button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button> <button type="button" class="btn btn-primary" data-dismiss="modal">' + modal.button + '</button></div></div>')
        }

        function get_server(action){
            if(settings.api.server == ""){
                return action
            }
            else{
                return settings.api.server
            }
        }
        
        function get_param_server(func, dict){
            if(settings.api.server == ""){
                return [func, dict]
            }
            else{
                $.extend(dict, {token: settings.api.token, method : "POST", function : action})
                return [settings.api.server, dict]
            }
        }
        
        /**
         *  @description Init the simulator
         */
        function init(){
            console.log("init simulator")
            
            init_vars();
            init_player();
            
            create_modal(settings.api.modal)
            
            if (settings.trace.activate) {
                init_trace();
            }

            
            params = get_param_server(settings.init.action, {state: settings.init.state})
            $.get(params[0], params[1],function(data){
                console.log(typeof(data))
                if (data.help)
                    init_help(data.help)

                console.log(_variables)
        
                set_modes(data.state);
                
                apply_trace(data.state);
                
                if (settings.graph.activate && data.state.variables && typeof(settings.graph) == typeof({}))
                    init_graph(data.state.variables, data.state.groups)
                
                print_option();
            });
            
            //add click event
            $(settings.api.quit).click(function() {
                console.log("quit");
                params = get_param_server("quit", {})
                $.get(params[0], params[1],function(data){
                    $("#alive .ui").html("").text(data);
                    window.location.reload();
                });
            });
            
            //add reset event
            $(settings.api.reset).click(function() {
                reset(instance_key)
            });
            
            $(settings.api.help).click(function(){
                console.log("change trigger");
                //We disabled the help
                if($(".help-ui").hasClass("help-activate")){
                    $(this).parent().removeClass("active");
                    $(".help-ui").removeClass("help-activate");
                    $(".help-ui").off( "mouseenter mouseleave" );
                }
                else{
                    $(this).parent().addClass("active");
                    $(".help-ui").addClass("help-activate");
                    $(".help-activate").hover(function(){
                        $(this).popover("show"); 
                        $(this).addClass("highlight_help")
                        event.stopImmediatePropagation();
                    },function(){
                        $(this).popover("hide"); 
                        $(this).removeClass("highlight_help")
                        event.stopImmediatePropagation();
                    });
                }
            });
            
            //add ping
            if (settings.api.token == ""){
                
                $("#alive .ping").text("Stayin alive!");
                $.periodic({period: 10000, decay:1, max_period: 10000}, function() {
                    params = get_param_server("ping", {})
                    $.get(params[0], params[1],function(data){
                        $(".ping").text(data);
                    });
                });
            }
            
            ul = $(settings.api.nav)
            
            $.each(settings.nav, function(key, value){
                li = document.createElement("li");
                a = document.createElement("a");                
        
                $(a).html(value.text);
                $(a).attr("href","#");
        
                $.each(value.attr, function(key, value){
                   $(a).attr(key,value);
                });
        
                $(li).append(a);
                $(ul).append(li);
            });
        }
        
        /**
         *  @description Add a trace to the history
         *  @param {Integer} key Contains the id where the trace will be set in history
         *  @param {Dict} trace  Contains all part to add at history, at max we use { trace: , modes: , variables: , data:}
         */
        function set_history(key, trace) {
            console.log("set_history")
            console.log(key)
            console.log(trace)
            $.each(trace, function(k,v){
                _history[k][key] = v
            })
            
        }
        
        /**
         *  @description Set modes to the history and to the view, like get_modes with update modes in history
         *  @param {Dict} data Contains all data for get states & modes
         */
        function set_modes(data){
            console.log("set_modes")
            
            //We have possibilité to do function in each state
            $.each(data.states, function (num, item) {
                update[item.do](item);
            });
            
            //New modes
            _modes = new Array();
        
            //For each modes & action, we create a list of modes
            $.each(data.modes, function(num, action){
                div = $(action.select);
                div.html("");
                
                div_group = document.createElement("div")
                
                $(div_group).addClass("btn-group-vertical")
        
        
                $.each(action.items, function (pos, item) {
                    button = document.createElement("button");
                    
                    newtrace = {
                        action : item.html,
                        mode : item.mode,
                        state : item.state,
                        groups : item.groups
                    };
                    
                    //We create the link for get the succ of this state
                    $(button).html(item.html)
                        .attr({
                            type: "button",
                            class: "btn btn-default"
                        })
                        
                    $(button).simisc().set_attr_link(newtrace, instance_key)
        
                    _modes.push(newtrace)
        
                    $(div_group).append(button);
                });
                
                $(div).append(div_group)
            });
        }
        
        /**
         *  @description Set modes to the history and to the view, like set_modes without update modes in history
         *  @param {Dict} data Contains all data for get states & modes
         */
        function get_modes(data) {
            console.log("get_modes")
            set_modes(data)
        }
        
        /**
         *  @description Reset the player to initial state, without call init
         */
        function reset(key){
            console.log("reset")
            _isHistory = false
            _clk_end = 0;
            _clk_begin = 0;
            cut_trace(0,1);
            
            //We get the data without pass by get_trace
            _trace = _history.trace[0]
            _variables = _history.variables[0]
            _modes = _history.modes[0]
            
            get_modes(_history.data[0])
            apply_trace(_history.data[0])
            print_option()
            console.log(_history)
        }
        
        /**
         *  @description Add a new trace to the history, call function @see set_modes, @see apply_trace and @see print_option
         *  @param {HTML Object} object Contain the object to calll the data from server
         *  @param {Integer} key Contain the key for settings (only use for 3.0)
         */
        $.simisc.set_trace = function(object, key){
            console.log("set_trace")
            _clk_end++;
            console.log(_clk_end)

            //TOBETTER
            tmp = document.createElement("a")
            
            $(tmp).html($(object).attr("data-action"))
            
            _trace = {
                "action": $(tmp).text(),
                "state": $(object).attr("data-state"),
                "mode": $(object).attr("data-mode")
            }
            
            console.log(_trace)
            
            params = get_param_server("succ", {state: _trace.state, mode: _trace.mode})
            $.get(params[0], params[1],function(data){
                if (settings.graph.activate && data.variables) {
                    _variables = data.variables
                    _variables.transition = _trace.action

                    if($(object).attr("data-groups"))
                        _variables.groups = $(object).attr("data-groups").split(",")
                }
                
                console.log(_history.variables)
                
                set_modes(data);
        
                apply_trace(data);
                
                print_option();
                
            });
        }
        
        /**
         *  @description Get a trace from the history, call function @see get_modes, @see apply_trace and @see print_option
         *  @param {HTML Object} object Contain the object to calll the data from server
         *  @param {Integer} key Contain the key for settings (only use for 3.0)
         */
        $.simisc.get_trace = function(object, key) {
            console.log("get_trace")
            console.log(_history)
            
            _clk_end = parseInt($(object).attr("data-num"),10);
            _isHistory = true;
            console.log(_clk_end)
            
            _trace = _history.trace[_clk_end]
            _variables = _history.variables[_clk_end]
            _modes = _history.modes[_clk_end]
            
            if (_clk_end == _history.trace.length-1) {
                _isHistory = false
            }
            
            get_modes(_history.data[_clk_end])
            apply_trace(_history.data[_clk_end]);
            print_option();
        }
        
        /**
         *  @description Apply the trace of current state, and check if we need to cut or juste set a new history
         *  @param {Dict} data Contain the data for the current state
         */
        function apply_trace(data) {
            console.log("apply_trace")
            console.log(_history)
            if (_isHistory) {
                if (!compare_trace(_history.trace[_clk_end], _trace)){
                    console.log("destroy jenkins");
                    console.log(_history)
                    console.log(_clk_end)
                    cut_trace(0,_clk_end)
                    console.log(_history)
                    _isHistory = false;
                }
                else{
                    console.log("get the old trace")
                    $.each(data.modes, function(num, action){
                        $(action.select + " button").each(function(){
                            console.log(this)
                            
                            if(compare_trace({"state":$(this).attr("data-state"), "mode":$(this).attr("data-mode")},_history.trace[_clk_end+1]))
                            {
                                console.log($(this))
                                $(this).addClass("btn-primary")
                                //We switch to get, because we know the content
                                $(this).simisc().get_attr_link(_clk_end+1, instance_key)
                                
                            }
                            else{
                                trace = {
                                    "action": $(this).attr("data-action"),
                                    "state": $(this).attr("data-state"),
                                    "mode": $(this).attr("data-mode"),
                                    "groups": $(this).attr("data-groups")
                                }
                                
                                $(this).simisc()
                                .addClass("btn-warning")
                                .on("click",function(){
                                    $(settings.api.modal.id + ' .btn-primary').simisc().set_attr_link(trace, instance_key)
                                    $(settings.api.modal.id).modal('show')
                                });
                            }
                        });
                    });
                }
            }
            console.log("set_history ici")
            console.log(_variables)
            
            set_history(_clk_end, {
                "trace": _trace,
                "variables": _variables,
                "modes": _modes,
                "data": data
            })
            
            update_command_center()
        }
        
        /**
         *  @description print on the view all option activated in the settings
         */
        function print_option() {
            console.log(_groups)
            if(settings.trace.activate && ('id' in settings.trace)){
                print_trace();
            }
            
            if(settings.graph.activate && ('id' in settings.graph)){
                print_graph();
            }
        }
            
        /**
         *  @description Delete from data all transition, where transition hasn't a group in activate groups.
         *  @param Array data All data to process in graph
         */
        function extract_groups(data) {
            console.log("extract_groups")
            data = jQuery.grep(data, function(v, i){                
                return (process_group(v.groups));
            })
            
            return data
        }
        
        /**
         *  @description Take an Array of groups and return true if one or more of this group are activate in control panel, false else.
         *  @param Array groups contains groups of current data to process
         */
        function process_group(groups) {
            console.log("process group")
            if (groups.length == 0) {
                console.log("length 0")
                return (_groups.indexOf("others") > -1)
            }
            else{
                ok = false
                
                for (g in groups) {
                    console.log(g)
                    if ( (g == "" && _groups.indexOf("others") > -1) || _groups.indexOf(groups[g]) > -1) {
                        ok = true
                    }
                }
                return ok
            }
        }
        
        /**
         * @description print the graph with the new data, use D3.js
         */
        function print_graph(){
            console.log("print_graph")
            $(settings.graph.id + " .tooltip").hide();
            
            _data = _history.variables
            _data = _data.slice(_clk_begin,_clk_end+1);
            
            _data = extract_groups(_data)
            
            if (_data.length == 1) {
                _data.push(_data[0])
            }
            
            taille = _data.length
            
            console.log("lance graphe avec")
            console.log(_history.variables);
            console.log(_data);
            console.log(_clk_end);
            
            //Update the x length
            _graph.x.domain([0, _data.length-1]);
        
            //Var for get the max for all variable
            var max = [0]
        
            //We destroy all point & text for var
            _graph.svg.selectAll(".text-var").remove();
            _graph.svg.selectAll("circle").remove();
        
            //We get the max only for actif variables
            _graph.variables.forEach(function(v){
                if ($(".check_var[var='" + v + "']").prop("checked") && taille > 0) {
                    max.push(d3.max(_data, function(d) { return d[v]; }));
                }
            });
            
            //Update the y axis
            _graph.y.domain([0, d3.max(max, function(d) { return d; })]);
        
            //Create the transition
            _graph.transition = d3.select(settings.graph.id).transition();
        
            //Update the number of tick on x axis
            _graph.xAxis.ticks(d3.min([_data.length, settings.graph.max_it]));
        
            //DO the translation for the axis object
            _graph.transition.select(".x.axis") 
                .duration(750)
                .call(_graph.xAxis)
                .selectAll("text")
                    .style("text-anchor", "end")
                    .style("cursor", "pointer")
                    .attr("dx", "-.8em")
                    .attr("dy", ".15em")
                    .attr("transform", function(d) {
                        return "rotate(-65)"
                    });
        
            //We update each actif variable, the text & circles too 
            _graph.variables.forEach(function(v){
                if ($(".check_var[var='" + v + "']").prop("checked") && taille > 0) {
                    console.log("variables")
                    console.log(v)
                    _graph.transition.select(".line-" + v)
                        .duration(750)
                        .attr("d", _graph.line[v](_data))
                        //Call back
                        .each("end",function(){
                            _graph.svg.selectAll("dot")
                                .data(_data)
                                .enter().append("circle")
                                .attr("r", 3.5)
                                .attr("cx", function(d, i) { return _graph.x(i); })
                                .attr("cy", function(d) { return _graph.y(d[v]); })
                                //We give the attr data-num for toggle the tooltip on this transition when axis x is hover
                                .attr("data-num", function(d,i) {
                                    //We create all tooltip 
                                    $(this).tooltip({
                                        'title': "transition " + d['transition'] + " : " + v + " = " + d[v],
                                        'trigger': 'manual',
                                        'container':"body"
                                    });
                                    
                                    return i;
                                })
                                .attr("style","cursor:pointer;fill:" + settings.graph.color[v])
                                .attr("class","dot dot-"+v)
                                .on("mouseover", function(d) {
                                    $(this).tooltip('show')
                                })
                                .on("mouseout", function(d){
                                    $(this).tooltip('hide')
                                })
                        });
                    
                    _graph.svg.append("text")
                        .attr("transform", "translate("+(_graph.width+10)+","+_graph.y(_data[taille-1][v])+")")
                        .attr("dy", ".35em")
                        .attr("text-anchor", "start")
                        .attr("class", "text-var text-"+v)
                        .style("fill", settings.graph.color[v])
                        .text(v);
                }
            });
        
                    
            //TODO : permet de faire la trace dans le graph : à améliorer pour direct le mettre dans le x axis, un peu brouillon a mon gout (c'est le compteur qui me gene)
            cmp = 0
        
            $(".x.axis text").each(function(){
                //text is empty when there isn't not enought transition pass
                if ($(this).html() != "") {
                    var tmp_clk = cmp;
                    
                    $(this).unbind("mouseover")
                        .mouseover(function(){
                            $(".dot[data-num=" + tmp_clk + "]").each(function(){
                                console.log($(this).css('opacity'))
                                if ( $(this).css('opacity') == 1 ) {
                                    $(this).tooltip('show')
                                }
                            });
                        })
                        .mouseout(function(){
                            $(".dot[data-num=" + tmp_clk + "]").each(function(){                    
                                $(this).tooltip('hide')
                            });
                        })            
                    cmp++
                }
            });
                    
            _graph.transition.select(".y.axis") // change the y axis
                .duration(750)
                .call(_graph.yAxis);
            
        }
        
        /**
         *  @description print the trace for see history
         */
        function print_trace(){
            console.log("print_trace")
        
            //At each state we rewrite the trace, can be optimised with prepend when just add, and add style when cross the path
            $("#simisc_trace").html("");
        
            $.each(_history.trace, function(key,value){
                a = document.createElement("a");
                td = document.createElement("td");
                tr = document.createElement("tr");
                title = ""
                span = document.createElement("span")
                
                $(span).addClass("glyphicon")
                $(tr).html("<td>" + key + "</td><td>" + value.action + "</td><td>" + value.mode + "</td><td>" + value.state + "</td>");
                
                if (settings.graph.interval && settings.graph.activate) {
                    //When interval we have a second part, for begin
                    tdb = document.createElement("td")
                    ab = document.createElement("a")
                    spanb = document.createElement("span")
                    titleb = ""
                    
                    $(spanb).addClass("glyphicon")
                    
                    if (key == _clk_end) {
                        $(tr).addClass("info")
                        $(span).addClass("glyphicon-arrow-left")
                        title = "current ending state"
                        
                        $(ab).click(function(){
                            change_begin(key)
                        })
                        $(spanb).addClass("glyphicon-indent-left")
                        titleb = "Set the new end interval"
                    }
                    //Part we can change the end interval
                    else if (key > _clk_begin) {
                        $(tr).addClass("warning")
                        $(a).simisc().get_attr_link(key,instance_key)
                        $(span).addClass("glyphicon-indent-right")
                        title = "Set the new end interval"
                        
                    }
                    
                    if (key == _clk_begin) {
                        $(tr).addClass("info")
                        $(spanb).addClass("glyphicon-arrow-right")
                        titleb = "current ending state"
                        
                        $(a).simisc().get_attr_link(key,instance_key)
                        $(span).addClass("glyphicon-indent-right")
                        title = "Set the new end interval"
                    }
                    //Part we can change the begin interval
                    else if (key < _clk_end) {
                        $(tr).addClass("warning")
                        $(ab).click(function(){
                            change_begin(key)
                        })
                        $(spanb).addClass("glyphicon-indent-left")
                        titleb = "Set the new end interval"
                    }
                    
                    if (key < _clk_end && key > _clk_begin) {
                        $(tr).removeClass("warning danger")
                        
                        if (settings.graph.groups && !process_group(_history.variables[key].groups)) {
                            $(tr).addClass("danger")
                        }
                        else{
                            $(tr).addClass("success")
                        }
                    }
                    
                    if (settings.graph.groups) {
                        $(tr).append("<td>" + _history.variables[key].groups.join(',') + "</td>")
                    }
                    
                    
                    $(ab).append(spanb)
                    $(tdb).append(ab)
                    
                    $(a).append(span)
                    $(td).append(a)
                    
                    $(tr).append(tdb,td)
                }
                //Normal mode without interval choice
                else{
                    if(key === _clk_end){
                        $(tr).addClass("info");
                        title = "current state"
                        $(span).addClass("glyphicon-arrow-left")
                    }
                    else{
                        $(tr).addClass("success");
                        $(span).addClass("glyphicon-share-alt")
                        $(a).simisc().get_attr_link(key, instance_key);
                    }
                    
                    if (key > _clk_end) {
                        $(tr).addClass("warning");
                    }
                    
                    
                    $(a).append(span)
                    $(td).append(a)
                    $(tr).append(td)
                }
                
                $("#simisc_trace").append(tr);
                
            });
        }    
        
        /**
         *  @description Compare a couple of 'state'/'mode'
         *  @returns {Boolean} True if the couple have same state & mode, false else
         */
        function compare_trace(t1,t2){
            if(t1.mode === t2.mode && t1.state === t2.state)
                return true;
            return false;
        }
        
        /**
         * @description Cut for trace all between the two param given
         * @param {Integer} begin The id where the cut is begin
         * @param {Integer} end The id where the cut is stop
         */
        function cut_trace(begin, end){
            console.log("cut_trace")
            
            $.each(_history, function(k,v){
                _history[k] = _history[k].slice(begin,end)
            })
        }
        
        /**
         *  @description Update value in interval of command center
         */
        function update_command_center(){
            console.log("update command center")
            $("#end_interval").val(_clk_end)
            $("#begin_interval").val(_clk_begin)
            $("#reset_interval").attr("data-num",_history.trace.length-1)  
        }
        
        /**
         *  @description Set the opacity to 1 to path with var : variable, if "not" is true is all path except this one will be toggle
         *  @param {String} variable Variable to show
         *  @param {Boolean} not If not is true all variables will be show except @see variable
         */
        function toggle_path(variable, not) {
            console.log("toogle_path")
            //Not mean : if you want toggle other than the path for the variable
            print_option()
            if (not) {
                $(".line:not(.line-"+ variable + ")").fadeTo("slow",1)
                $(".dot:not(.dot-"+ variable + ")").fadeTo("slow",1)
                $(".text-var:not(.text-"+ variable + ")").fadeTo("slow",1)
            }
            else{
                $(".line-" + variable).fadeTo("slow",1)
                $(".dot-" + variable).fadeTo("slow",1)
                $(".text-" + variable).fadeTo("slow",1)
            }
        }
        
        /**
         *  @description Set the opacity to 0 to path with var : variable, if "not" is true is all path except this one will be fade
         *  @param {String} variable Variable to hide
         *  @param {Boolean} not If not is true all variables will be hide except @see variable
         */
        function fade_path(variable, not){
            print_option()
            if (not) {
                $(".line:not(.line-"+ variable + ")").fadeTo("slow",0)
                $(".dot:not(.dot-"+ variable + ")").fadeTo("slow",0)
                $(".text-var:not(.text-"+ variable + ")").fadeTo("slow",0)
            }
            else{
                $(".line-" + variable).fadeTo("slow",0)
                $(".dot-" + variable).fadeTo("slow",0)
                $(".text-" + variable).fadeTo("slow",0)
            }
        }
        
    };
    
    //For the 3.0 version : multiple simulators in same time
    $.simisc.instance = new Array()
    
    //The default value for simulator
    $.simisc.defaults = {
        "api":{
            //Id for reset button
            "reset": "#ui-reset",
            //If localhost let him empty
            "token": "",
            //Server for call function, if you are in localhost let him empty
            "server":"",
            //Id for stop button
            "quit": "#ui-quit",
            //Id for help button
            "help":"#ui-help",
            //Where model is stock
            "model": "#model",
            //Where nav will be added
            "nav": "#nav_sim",
            "modal":{
                "id":"#simisc_trace_alert",
                "text":"The trace isn't same as history, will you change this trace ?",
                "title":"Warning : new trace detected",
                "button": "Go new trace"
            },
        },
        //Where is the player & if he is activate
        "player":{
            //Where the player is added
            "id":"#player",
            "modal":{
                "id":"#simisc_player_alert",
                "text":"The trace isn't same as history, will you change this trace ?",
                "title":"Warning : new trace detected",
                "button": "Go new trace"
            },
            //When true the player will be add
            "activate": true
        },
        //Nav optionnal content, add to reset/quit & help button
        "nav": {
            //Sample of new content to nav
            "about": {
                "script": "",
                "text": "About",
                "attr": {
                    "data-toggle": "modal",
                    "data-target": "#ui-about"
                }
            }
        },
        //Init state
        "init": {
            "state": 0,
            "mode": 0,
            //How we call the init state
            "action": "init",
            "groups": Array()
        },
        //Option for trace
        "trace": {
            //Where the trace will be added
            "id": "#trace_zone",
            //If the trace is activated
            "activate": true
        },
        //Option for graph
        "graph": {
            //Where the graph will be added
            'id' : '#graph',
            'control_panel': '#Command_center',
            //The number max of tick with label in x axis
            "max_iteration" : 50,
            //If we can change the begin & the end for zoom in graph
            "interval": true,
            //Where the command pannel will be add
            "command_bord": "#graph_bord",
            //If the graph is activated
            "activate": true,
            //If typed transition are active
            "groups": true
        }
    };

})(jQuery)
