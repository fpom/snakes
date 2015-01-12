$(document).ready(function(){
    $(".abcd .action, .abcd .instance").each(function(){
        var objet = this;
        $(".action, .instance").each(function(){
            if ($(this).attr("data-abcd") == "#" + $(objet).attr("id")){
                $(this).html($(objet).html());
            }
        });
    });

    $(".action, .instance, .buffer, .proto").mouseover(function(){

        $(this).addClass("highlight_simul");
        $($(this).attr("data-abcd")).addClass("highlight_simul");
        $($(this).attr("data-tree")).addClass("highlight_simul");
        $($(this).attr("data-net")).addClass("highlight_simul");

    }).mouseout(function(){

        $(this).removeClass("highlight_simul");
        $($(this).attr("data-abcd")).removeClass("highlight_simul");
        $($(this).attr("data-tree")).removeClass("highlight_simul");
        $($(this).attr("data-net")).removeClass("highlight_simul");

    });
});